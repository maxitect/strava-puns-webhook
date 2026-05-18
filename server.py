import os
import sqlite3
import threading
import time
import requests
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from dotenv import load_dotenv, set_key

load_dotenv()

app = Flask(__name__)

DB_PATH = os.getenv("DB_PATH", "puns.db")
WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN")
STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
RIDE_TYPES = {"Ride", "EBikeRide", "VirtualRide", "GravelRide", "MountainBikeRide"}

_token_cache = {
    "access_token": None,
    "expires_at": 0,
}
_token_lock = threading.Lock()


def get_access_token():
    with _token_lock:
        if (
            _token_cache["access_token"]
            and time.time() < _token_cache["expires_at"] - 60
        ):
            return _token_cache["access_token"]

        refresh_token = os.getenv("STRAVA_REFRESH_TOKEN")
        resp = requests.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id": STRAVA_CLIENT_ID,
                "client_secret": STRAVA_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        _token_cache["access_token"] = data["access_token"]
        _token_cache["expires_at"] = data["expires_at"]

        env_path = os.path.join(os.path.dirname(__file__), ".env")
        set_key(env_path, "STRAVA_REFRESH_TOKEN", data["refresh_token"])
        os.environ["STRAVA_REFRESH_TOKEN"] = data["refresh_token"]

        return _token_cache["access_token"]


def pick_pun():
    conn = sqlite3.connect(DB_PATH)
    with conn:
        row = conn.execute(
            "SELECT id, title FROM puns WHERE used_at IS NULL ORDER BY RANDOM() LIMIT 1"
        ).fetchone()
        if not row:
            row = conn.execute(
                "SELECT id, title FROM puns ORDER BY used_at ASC LIMIT 1"
            ).fetchone()
        now = datetime.now(timezone.utc).isoformat()
        conn.execute("UPDATE puns SET used_at = ? WHERE id = ?", (now, row[0]))
    conn.close()
    return row[1]


def process_activity(activity_id):
    try:
        token = get_access_token()
        headers = {"Authorization": f"Bearer {token}"}

        resp = requests.get(
            f"https://www.strava.com/api/v3/activities/{activity_id}",
            headers=headers,
        )
        resp.raise_for_status()
        activity = resp.json()

        sport_type = activity.get("sport_type")
        print(f"Activity {activity_id} received, sport_type={sport_type}")

        if sport_type not in RIDE_TYPES:
            print(f"Activity {activity_id} is not a ride type, skipping")
            return

        pun = pick_pun()
        print(f"Selected pun: {pun}")

        result = requests.put(
            f"https://www.strava.com/api/v3/activities/{activity_id}",
            headers=headers,
            json={"name": pun},
        )
        result.raise_for_status()
        print(f"Activity {activity_id} renamed to: {pun}")
    except Exception as e:
        print(f"Error processing activity {activity_id}: {e}")


@app.route("/webhook", methods=["GET"])
def webhook_verify():
    mode = request.args.get("hub.mode")
    verify_token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and verify_token == WEBHOOK_VERIFY_TOKEN:
        return jsonify({"hub.challenge": challenge}), 200
    return "", 403


@app.route("/webhook", methods=["POST"])
def webhook_receive():
    event = request.get_json()
    if event.get("object_type") == "activity" and event.get("aspect_type") == "create":
        activity_id = event.get("object_id")
        threading.Thread(
            target=process_activity, args=(activity_id,), daemon=True
        ).start()
    return "", 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
