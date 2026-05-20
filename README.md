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

### 5. Add puns list

Copy `puns.json` to the project directory. This file is gitignored — manage it locally.

### 6. Deploy with Docker

Ensure the `cf-tunnel` external network exists on the host and set it up with your own tunnel access:

```bash
docker network create cf-tunnel
```

Then start the container:

```bash
docker compose up -d
```

On first start (no `puns.db` present), the container automatically runs `init_db.py` — creates the database, seeds puns from `puns.json`, and backfills used puns from your Strava history. Subsequent restarts skip this step.

### 7. Register the Strava webhook

```bash
curl -X POST https://www.strava.com/api/v3/push_subscriptions \
  -d client_id=YOUR_CLIENT_ID \
  -d client_secret=YOUR_CLIENT_SECRET \
  -d callback_url=https://yoursite.com/webhook \
  -d verify_token=YOUR_WEBHOOK_TOKEN
```

### 8. Verify the subscription

```bash
curl "https://www.strava.com/api/v3/push_subscriptions?client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET"
```

## Adding new puns

**Option A** — directly in the database:

```bash
docker exec -it strava-puns-webhook sqlite3 puns.db "INSERT OR IGNORE INTO puns (title) VALUES ('My New Pun');"
```

**Option B** — append to `puns.json` and re-run `init_db.py`:

```bash
docker exec strava-puns-webhook python init_db.py
```

Re-running is safe; `INSERT OR IGNORE` won't overwrite existing rows.

Note: `puns.json` is gitignored — edit it locally and it's bind-mounted into the container.
