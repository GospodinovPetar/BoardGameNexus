# BoardGame Nexus

BoardGame Nexus is a Django app for board game fans. It’s built around a simple idea: keep a clean catalog of games, plan game nights (events), and share reviews—plus a small REST API for the same data.

You can run it as a classic server-rendered Django site (Bootstrap UI) and also browse the API through Swagger.

## What you can do in the app

- **Browse games**: a genre-based catalog of board games with optional images (URL or upload).
- **Search & filter**:
  - **Games**: filter by title, genres, rating range (community average), players, and release date.
  - **Events**: filter by name, organizer, locations, date range, players, and linked games.
- **Events**:
  - Create events and link them to one or more games.
  - Join an event until it reaches capacity (joining is tracked in the user’s session).
- **Reviews**:
  - Create, edit, and delete reviews.
  - Enforced rule: **one review per user per game**, rating **1–5**.
  - Reviews list supports filtering by a game via `?game=<id>`.
- **Accounts & profiles**:
  - Custom user model with **bio**, **avatar**, and **date of birth**.
  - Auto-created `UserProfile` with extra fields (favourite genre, games played, location).
- **Collections**:
  - Track games as: **Want to Play / Currently Playing / Played / Owned** (plus notes).
- **REST API**:
  - DRF endpoints for games, events, reviews, collections, and the current user.
  - Swagger UI at `/api/docs/`.

## Roles / permissions (how moderation works)

The project uses two Django groups:

- **Members**: regular users (review + collection permissions).
- **Moderators**: allowed to manage games and events.

These groups are created by the `accounts.0002_create_user_groups` migration.

## Tech stack

- **Backend**: Django 6.0.2, Django REST Framework
- **DB**: PostgreSQL
- **Cache/broker**: Redis (for Celery)
- **Background jobs**: Celery
- **UI**: Bootstrap 5, `django-crispy-forms` + `crispy-bootstrap5`
- **Admin theme**: `django-jazzmin`
- **API schema/docs**: `drf-spectacular` (OpenAPI + Swagger UI)
- **Config**: `python-dotenv` (loads `.env`)

## Quickstart (Docker)

This is the easiest way to run the whole stack (Postgres + Redis + Django + Celery).

```bash
cp .env.example .env
docker compose up --build
```

This starts:
- `db` (Postgres)
- `redis`
- `web` (Django dev server on port 8000)
- `celery` (worker for background tasks like welcome emails)

On startup, the `web` service runs migrations and loads the initial fixture.

Open the app at `http://127.0.0.1:8000/`.

### Helpful Docker commands

```bash
# stop containers
docker compose down

# rebuild after code or dependency changes
docker compose up --build

# start in background
docker compose up -d --build

# view logs
docker compose logs -f
```

## Local development (optional, no Docker)

```bash
cp .env.example .env

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py loaddata initial_data.json

# Terminal 1: Django
python manage.py runserver

# Terminal 2: Celery worker
celery -A BoardGameNexus worker -l info
```

## Environment variables

The project reads config from `.env` (loaded via `python-dotenv`).

### Django / host

- **`SECRET_KEY`**: Django secret key
- **`DEBUG`**: `True/False` (currently set in settings for development)
- **`ALLOWED_HOSTS`**: comma-separated (e.g. `localhost,127.0.0.1`)

### Database (Postgres)

- **`DB_NAME`**
- **`DB_USER`**
- **`DB_PASSWORD`**
- **`DB_HOST`**: local dev is usually `127.0.0.1`, Docker Compose uses `db`
- **`DB_PORT`**: usually `5432`

### Celery / Redis

- **`CELERY_BROKER_URL`**: default `redis://redis:6379/0` in Docker
- **`CELERY_RESULT_BACKEND`**: default `redis://redis:6379/0` in Docker

### Email (SMTP)

Email is configured via env vars. If `SMTP_HOST` is empty, Django falls back to the **console email backend** (prints emails to the server logs).

- **`DEFAULT_FROM_EMAIL`**
- **`SMTP_HOST`**
- **`SMTP_PORT`** (Gmail typically `587`)
- **`SMTP_USERNAME`**
- **`SMTP_PASSWORD`** (use an app password)
- **`SMTP_USE_TLS`** (`true/false`)
- **`SMTP_USE_SSL`** (`true/false`)

## Deploying to Azure App Service (quick notes)

This repo is set up to serve static files with **WhiteNoise** (so you don’t need a separate CDN just to get going).

- **Startup command**: set your App Service startup command to run `startup.sh` (or run the equivalent command directly).
- **Required app settings**: configure the same env vars as in `.env.example` (at minimum `SECRET_KEY` + DB settings).
- **Static files**: `startup.sh` runs `collectstatic` and WhiteNoise serves from `staticfiles/`.

## Key routes

### Web

- `/` — Home
- `/mission/`, `/contact/` — Static pages
- `/games/` — Games list + filters
- `/events/` — Events list + filters
- `/reviews/` — Reviews list (supports `?game=<id>`)
- `/accounts/register/`, `/accounts/login/`, `/accounts/profile/`
- `/admin/` — Django admin

### API

Base path is **`/api/`**.

- `GET /api/genres/`
- `GET/POST /api/games/`
- `GET/PATCH/DELETE /api/games/<id>/`
- `GET/POST /api/events/`
- `GET/PATCH/DELETE /api/events/<id>/`
- `GET/POST /api/reviews/`
- `GET/PATCH/DELETE /api/reviews/<id>/`
- `GET/POST /api/collections/` (requires login)
- `GET/PATCH/DELETE /api/collections/<id>/` (requires login + ownership/moderator)
- `GET/PATCH /api/users/me/` (requires login)
- `POST /api/auth/token/` (DRF token auth)

API docs:
- **Swagger UI**: `/api/docs/`
- **OpenAPI schema**: `/api/schema/`

## Background tasks (Celery)

- **Welcome email**: sent after a new user account is created (only if the user has an email).
- **Weekly digest** (`games.tasks.send_weekly_digest`): currently logs a simple digest (counts of games/events/reviews).

## Fixtures

There’s a starter dataset at `games/fixtures/initial_data.json` (genres + a few games and events).

Load it with:

```bash
python manage.py loaddata initial_data.json
```

## Running tests

```bash
python manage.py test accounts games reviews events api web --verbosity=2
```

## Project structure

```
BoardGameNexus/
├── BoardGameNexus/  # Settings, root URLs, Celery config
├── accounts/        # Custom user + profile, auth views, welcome email task
├── api/             # DRF API (views, serializers, permissions, urls)
├── events/          # Events + search form
├── games/           # Games + genres + weekly digest task
├── reviews/         # Reviews + collections
├── web/             # Home/mission/contact pages + error handlers
├── templates/       # HTML templates
├── static/          # Project-wide static files
└── media/           # Uploaded files (created at runtime)
```
