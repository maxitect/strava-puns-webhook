# strava-puns-webhook

Webhook server that renames new Strava cycling activities with cycling-themed film/TV puns.

## Setup

### 1. Install dependencies

```bash
poetry install
```

### 2. Create a Strava API app

Go to https://www.strava.com/settings/api and create an application. Note your **Client ID** and **Client Secret**.

### 3. Obtain a refresh token

You need a token with `activity:read,activity:write` scope.

**Step 1 — open this URL in your browser** (replace `YOUR_CLIENT_ID`):

```
https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=activity:read,activity:write
```

Authorise the app. You'll be redirected to a URL like:

```
http://localhost/?state=&code=AUTHORIZATION_CODE&scope=read,activity:read,activity:write
```

Copy the `code` value.

**Step 2 — exchange the code for tokens**:

```bash
curl -X POST https://www.strava.com/oauth/token \
  -d client_id=YOUR_CLIENT_ID \
  -d client_secret=YOUR_CLIENT_SECRET \
  -d code=AUTHORIZATION_CODE \
  -d grant_type=authorization_code
```

Copy the `refresh_token` from the response.

### 4. Configure environment variables

```bash
cp .env.example .env
```

Fill in `.env`:

```
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
STRAVA_REFRESH_TOKEN=your_refresh_token
WEBHOOK_VERIFY_TOKEN=any_secret_string_you_choose
DB_PATH=puns.db
PORT=5000
```

### 5. Initialise the database

```bash
poetry run python init_db.py
```

This creates `puns.db`, seeds puns from `puns.json`, inserts past ride names from your Strava history as already-used, and marks any puns whose titles match past activity names.

### 6. Expose port publicly

Expose the server port via your preferred tunnel or reverse proxy so Strava can reach it. Note the public URL (e.g. `https://webhook.yourdomain.com`).

### 7. Start the server

```bash
poetry run python server.py
```

### 8. Register the Strava webhook

```bash
curl -X POST https://www.strava.com/api/v3/push_subscriptions \
  -d client_id=YOUR_CLIENT_ID \
  -d client_secret=YOUR_CLIENT_SECRET \
  -d callback_url=https://YOUR_PUBLIC_URL/webhook \
  -d verify_token=YOUR_WEBHOOK_VERIFY_TOKEN
```

### 9. Verify the subscription

```bash
curl "https://www.strava.com/api/v3/push_subscriptions?client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET"
```

## Running as a systemd service

Create `/etc/systemd/system/strava-puns.service`:

```ini
[Unit]
Description=Strava Puns Webhook
After=network.target

[Service]
User=maxime
WorkingDirectory=/home/maxime/strava-puns-webhook
EnvironmentFile=/home/maxime/strava-puns-webhook/.env
ExecStart=/home/maxime/.local/bin/poetry run python server.py
Restart=on-failure
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable strava-puns
sudo systemctl start strava-puns
sudo journalctl -u strava-puns -f
```

## Adding new puns

**Option A** — directly in the database:

```bash
sqlite3 puns.db "INSERT OR IGNORE INTO puns (title) VALUES ('My New Pun');"
```

**Option B** — append to `puns.json` and re-run `init_db.py`:

```bash
poetry run python init_db.py
```

Re-running is safe; `INSERT OR IGNORE` won't overwrite existing rows.

Note: `puns.json` is gitignored — edit it locally to customise your pun list.
