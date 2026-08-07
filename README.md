# Allie Care App

Personal care dashboard for Allie (Morelia bredli) — FastAPI + Postgres + React/Tailwind.

## Stack

- `apps/api` — FastAPI, SQLAlchemy, Alembic
- `apps/web` — React, Vite, Tailwind
- Postgres on Railway (or Docker Compose locally)

## Local development

### 1. Database

```bash
docker compose up -d db
```

### 2. API

```bash
cd apps/api
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg2://allie:allie@localhost:5432/allie
export APP_PASSWORD=allie
export APP_SECRET=dev-secret
export WEB_ORIGIN=http://localhost:5173
export RESEND_API_KEY=           # from Resend dashboard (never commit)
export RESEND_FROM="Allie Care <onboarding@resend.dev>"
export CRON_SECRET=dev-cron-secret
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Email digests + cron

Settings in the app control destination email, timezone, digest times, care intervals, and which event emails fire.

Secrets stay in env: `RESEND_API_KEY`, `RESEND_FROM`, `CRON_SECRET`.

Every minute, hit the tick endpoint (local loop or Railway cron):

```bash
curl -X POST http://127.0.0.1:8000/api/internal/tick \
  -H "X-Cron-Secret: $CRON_SECRET"
```

- Digests send when local time matches Settings digest times (default 08:00 and 20:00 America/Chicago)
- Tick also evaluates handle-cleared / feed-overdue / handling-gap events
- Shed blue/opaque and regurg emails fire on write

Use **Settings → Send test digest** after setting `RESEND_API_KEY` and destination email.

### 3. Web

```bash
cd apps/web
npm install
npm run dev
```

Open http://localhost:5173 — password defaults to `allie`.

### Full stack via Docker

```bash
docker compose up --build
```

- Web: http://localhost:8080  
- API: http://localhost:8000  

## Railway deploy

1. Create a Railway project and add a **Postgres** plugin.
2. Create service **api** from this repo:
   - Root / Dockerfile: `apps/api/Dockerfile`
   - Variables:
     - `DATABASE_URL` (from Postgres reference)
     - `APP_PASSWORD` — shared login password
     - `APP_SECRET` — random secret for tokens
     - `WEB_ORIGIN` — public web URL
     - `UPLOAD_DIR=/data/uploads`
     - `RESEND_API_KEY`
     - `RESEND_FROM`
     - `CRON_SECRET`
   - Attach a **volume** at `/data`
   - Add a **cron** (every minute) to `POST /api/internal/tick` with header `X-Cron-Secret`
3. Create service **web** from `apps/web/Dockerfile`:
   - Build arg / env `VITE_API_URL` = public API URL (no trailing slash)
4. After deploy, log in and use **Settings → Import** to migrate old `localStorage` data if needed.

## Tests

```bash
cd apps/api && .venv/bin/pytest tests/ -q
```

## Features

Feeds (with prey weight), weights, regurgitations, handling, shed cycles, env readings, eliminations, maintenance, photos, treatments, vet visits, contacts, journal, reminders on Overview, JSON/CSV export, Resend digests + event emails, customizable Settings.
