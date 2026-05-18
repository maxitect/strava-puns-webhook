import json
import os
import sqlite3
import requests
from dotenv import load_dotenv, set_key

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "puns.db")
STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")

_puns_path = os.path.join(os.path.dirname(__file__), "puns.json")
with open(_puns_path) as _f:
    PUNS = json.load(_f)


def get_access_token():
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
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    set_key(env_path, "STRAVA_REFRESH_TOKEN", data["refresh_token"])
    os.environ["STRAVA_REFRESH_TOKEN"] = data["refresh_token"]
    return data["access_token"]


def fetch_all_activities(token):
    activities = {}
    page = 1
    headers = {"Authorization": f"Bearer {token}"}
    while True:
        resp = requests.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers=headers,
            params={"per_page": 200, "page": page},
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        for a in batch:
            activities[a["name"]] = a["start_date"]
        page += 1
    return activities


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS puns (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            title   TEXT NOT NULL UNIQUE,
            used_at DATETIME NULL
        )
    """)
    conn.commit()

    inserted = 0
    for pun in PUNS:
        cur = conn.execute("INSERT OR IGNORE INTO puns (title) VALUES (?)", (pun,))
        inserted += cur.rowcount
    conn.commit()

    print(f"Puns inserted: {inserted}")

    token = get_access_token()
    activities = fetch_all_activities(token)
    print(f"Strava activities fetched: {len(activities)}")

    seeded_from_history = 0
    marked = 0
    for name, start_date in activities.items():
        cur = conn.execute(
            "INSERT OR IGNORE INTO puns (title, used_at) VALUES (?, ?)",
            (name, start_date),
        )
        seeded_from_history += cur.rowcount
        cur = conn.execute(
            "UPDATE puns SET used_at = ? "
            "WHERE title = ? AND used_at IS NULL",
            (start_date, name),
        )
        marked += cur.rowcount
    conn.commit()
    conn.close()

    print(f"Puns seeded from Strava history: {seeded_from_history}")
    print(f"Puns marked as used from history: {marked}")


if __name__ == "__main__":
    main()
