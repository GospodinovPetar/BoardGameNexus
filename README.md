# BoardGame Nexus

BoardGame Nexus is a Django platform for board game communities in Bulgaria. It connects **events**, **partner venues**, and **players** — with live [BoardGameGeek](https://boardgamegeek.com/) (BGG) search for picking games, venue-backed bookings, and a REST API for integrations.

The site is server-rendered (Bootstrap 5 dark theme) with a small JavaScript layer for the BGG game picker and venue availability. API docs are available via Swagger.

## What you can do

### Events

- Browse upcoming public events with search and filters (name, organizer, location, dates, player counts, linked games).
- Create and edit events (moderators and authenticated organizers).
- Join or leave events until capacity is reached (`EventRegistration` in the database).
- Pick games via an embedded **BGG search picker**; selected games are cached locally as `BoardGame` rows.
- At **partner venues**, events book a table slot automatically. The game picker is restricted to that venue’s library, and **recommended picks** come from the venue catalog (not the global list).
- Organizers can mark attendance and remove participants; join/leave triggers optional Celery emails.

### Partner venues

- Browse active venues at `/venues/` with filters for name and city, plus cards showing game count and review ratings.
- Venue detail pages show location, hours, table capacity, linked games, and reviews.
- **Venue staff** get a dashboard (`/venues/dashboard/`) to manage reservations, search bookings, and cancel venue-backed events.
- Staff and moderators can **edit venues** and manage the venue game library via the same BGG picker used on events.
- **Venue reviews**: one review per user per venue (rating 1–5), listed on the venue page.

### Games (BGG-backed, not a public catalog)

There is **no** public `/games/` browse page. `BoardGame` is an internal cache populated when users pick games on event or venue forms, or via the API `ensure` endpoint. Game titles link out to BGG (`bgg_url`).

BGG integration features:

- Live search with **24h Redis cache**, **7d stale fallback**, and **single-flight locking** for concurrent requests.
- Retries on BGG gateway errors (502/503/504) with user-friendly error messages.
- Stale cache responses include the `X-BGG-Cache: stale` header.
- **Global recommended** top 5 (by BGG rank) for open-location events via `GET /api/games/recommended/`.
- **Venue recommended** top 5 from a venue’s library via `GET /api/venues/<id>/recommended-games/` (24h Redis cache per venue).

### Game reviews & collections

- **Game reviews** at `/reviews/` (not in the main navbar): create, edit, delete; one review per user per game; rating 1–5; filter with `?game=<id>`.
- **User collections** (Want to Play / Currently Playing / Played / Owned) via the API and profile.

### Accounts & profiles

- Custom user model: username, email, bio, avatar, date of birth.
- Auto-created `UserProfile` (favourite genre, games played, location).
- Register, login (crispy forms), password reset, password change, public profile pages.

### Home & navigation

- Home shows counts for **Active Events** and **Partner Venues** with links to each hub.
- Flat top nav: **Events · Venues · Mission · Contact** (+ Dashboard for venue staff, Profile / Log out when signed in).

## Roles & permissions

Django groups (created by `accounts.0002_create_user_groups`):

| Group | Capabilities |
|-------|----------------|
| **Members** | Join events, write game/venue reviews, manage collections |
| **Moderators** | Create/edit/delete events and venues |
| **Venue staff** | Assigned per venue (`Venue.staff`); access venue dashboard and edit their venues |

Superusers have full admin access.

## Tech stack

| Layer | Choice |
|-------|--------|
| Backend | Django 6.0.2, Django REST Framework |
| Database | PostgreSQL |
| Cache / broker | Redis (Django cache for BGG + Celery broker) |
| Background jobs | Celery |
| UI | Bootstrap 5, django-crispy-forms + crispy-bootstrap5 |
| Admin | django-jazzmin |
| API docs | drf-spectacular (OpenAPI + Swagger UI) |
| Static files | WhiteNoise |
| Config | python-dotenv (`.env`) |

## Quickstart (Docker)

Recommended way to run the full stack (Postgres + Redis + Django + Celery).

```bash
cp .env.example .env
# Add BGG_API_KEY — required for game search/picker (see Environment variables)
docker compose up --build
```

This starts:

- `db` — PostgreSQL
- `redis` — cache and Celery broker
- `web` — Django on port **8000** (runs migrations + loads fixture on startup)
- `celery` — worker (welcome emails, event reminders, digest)

Open **http://127.0.0.1:8000/**

> **Note:** The Docker image copies application code at build time (no live source mount). After changing Python, templates, or static files, rebuild with `docker compose up --build`.

### Helpful Docker commands

```bash
docker compose down
docker compose up --build
docker compose up -d --build
docker compose logs -f web

# Run tests inside the web container
docker compose exec web python manage.py test --verbosity=2

# Create a superuser
docker compose exec web python manage.py createsuperuser
```

## Local development (without Docker)

```bash
cp .env.example .env

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py loaddata initial_data.json

# Terminal 1
python manage.py runserver

# Terminal 2
celery -A BoardGameNexus worker -l info
```

Use `DB_HOST=localhost` and `CELERY_BROKER_URL=redis://localhost:6379/0` in `.env` when Redis/Postgres run locally.

## Environment variables

Loaded from `.env` via `python-dotenv`.

### Django / host

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True`/`False` — Docker `web` service forces `DEBUG=true` for static/media |
| `SERVE_MEDIA_IN_APP` | Serve `/media/` from Django when `True` (dev/Docker) |
| `ALLOWED_HOSTS` | Comma-separated hostnames |
| `CSRF_TRUSTED_ORIGINS` | Optional; auto-includes localhost when `DEBUG=true` |

### Database

| Variable | Default / notes |
|----------|-----------------|
| `DB_NAME` | `boardgamenexus` |
| `DB_USER` | `boardgame` (Docker) / `postgres` (local example) |
| `DB_PASSWORD` | — |
| `DB_HOST` | `db` in Docker, `localhost` locally |
| `DB_PORT` | `5432` |

### Celery / Redis

| Variable | Default |
|----------|---------|
| `CELERY_BROKER_URL` | `redis://redis:6379/0` (Docker) |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/0` |

### BoardGameGeek (required for picker & search)

| Variable | Description |
|----------|-------------|
| `BGG_API_KEY` | Bearer token from [BGG Applications → Tokens](https://boardgamegeek.com/applications). Aliases: `BGG_APPLICATION_TOKEN`, `BGG_TOKEN`, `BGG_AUTH_TOKEN`. |
| `BGG_RECOMMENDED_CANDIDATE_IDS` | Optional comma-separated BGG ids for the global top-5 pool (`GET /api/games/recommended/`). |

**BGG request optimization** (to stay within API limits):

- **Search** (`/search`): cached 24h in Redis (+ 7d stale fallback); one BGG call per unique query.
- **Thing/geekitem** (`/thing`): cached **7 days** per `bgg_id` in Redis; batched up to **20 ids per request**.
- **Ensure** (`POST /api/games/ensure/`): bulk DB lookup + one batched `/thing` call for missing ids only.
- **Recommended**: stats fetched in batches; local `BoardGame` rows created from summary data **without** a second `/thing` round-trip.
- **Venue recommended**: ranks at most **40** games from the venue library; results cached 24h per venue.
- **UI**: clicking **Add** on a recommended card uses the local id when available — no extra ensure/thing call.

### Email (SMTP)

If `SMTP_HOST` is empty, emails print to the console (dev).

| Variable | Notes |
|----------|-------|
| `DEFAULT_FROM_EMAIL` | |
| `SMTP_HOST`, `SMTP_PORT` | Gmail typically port `587` |
| `SMTP_USERNAME`, `SMTP_PASSWORD` | App password for Gmail |
| `SMTP_USE_TLS`, `SMTP_USE_SSL` | `true`/`false` |

## Key routes

### Web

| Path | Description |
|------|-------------|
| `/` | Home (event + venue counts) |
| `/mission/`, `/contact/` | Static pages |
| `/events/` | Event list, filters, create/edit/delete, join/leave |
| `/events/<id>/` | Event detail |
| `/venues/` | Partner venue hub (search, cards) |
| `/venues/<slug>/` | Venue detail |
| `/venues/<slug>/reviews/` | Venue reviews |
| `/venues/dashboard/` | Staff reservation dashboard |
| `/venues/edit/<slug>/` | Edit venue + game library |
| `/reviews/` | Game reviews (supports `?game=<id>`) |
| `/accounts/register/`, `/login/`, `/profile/` | Auth & profiles |
| `/admin/` | Django admin (Jazzmin) |

### API

Base path: **`/api/`**

**Games (BGG proxy + cache — no public game CRUD)**

| Method | Path | Auth |
|--------|------|------|
| `GET` | `/api/games/search/?q=` | Public |
| `GET` | `/api/games/recommended/` | Public |
| `POST` | `/api/games/ensure/` | Public |
| `GET` | `/api/venues/<id>/games/` | Public |
| `GET` | `/api/venues/<id>/recommended-games/` | Public |

**Events, reviews, collections, user**

| Method | Path | Auth |
|--------|------|------|
| `GET/POST` | `/api/events/` | Read public; write authenticated |
| `GET/PATCH/DELETE` | `/api/events/<id>/` | Read public; write owner/moderator |
| `GET/POST` | `/api/reviews/` | Read public; write authenticated |
| `GET/PATCH/DELETE` | `/api/reviews/<id>/` | Read public; write owner/moderator |
| `GET/POST` | `/api/collections/` | Authenticated |
| `GET/PATCH/DELETE` | `/api/collections/<id>/` | Owner or moderator |
| `GET/PATCH` | `/api/users/me/` | Authenticated |
| `POST` | `/api/auth/token/` | DRF token auth |

**Documentation**

| Path | Description |
|------|-------------|
| `/api/docs/` | Swagger UI |
| `/api/schema/` | OpenAPI schema |

## Background tasks (Celery)

| Task | Trigger |
|------|---------|
| Welcome email | New user registration (if email set) |
| Event join confirmation | User joins an event |
| Event reminders | Scheduled 1 day and 2 hours before start |
| Weekly digest | `games.tasks.send_weekly_digest` — logs counts (games/events/reviews) |

## Fixtures

Starter data: `games/fixtures/initial_data.json` — sample `BoardGame` rows and demo events.

```bash
python manage.py loaddata initial_data.json
```

Docker loads this automatically on `web` startup.

## Running tests

```bash
python manage.py test accounts games reviews events venues api web --verbosity=2
```

Or inside Docker:

```bash
docker compose exec web python manage.py test --verbosity=2
```

## Deploying to Azure App Service

- Static files: **WhiteNoise** + `collectstatic` in `startup.sh`.
- Set the same env vars as `.env.example` (minimum: `SECRET_KEY`, database, `ALLOWED_HOSTS`, `BGG_API_KEY`).
- Startup command: run `startup.sh` or equivalent (`gunicorn` + migrate + collectstatic).

## Project structure

```
BoardGameNexus/
├── BoardGameNexus/     # Settings, root URLs, Celery, WSGI
├── accounts/           # Custom user, profiles, auth views, welcome email
├── api/                # DRF views, serializers, BGG API endpoints
├── events/             # Events, registrations, visibility rules
├── games/              # BoardGame cache, BGG services, game picker
│   └── services/       # bgg.py, cache.py, recommended.py
├── reviews/            # GameReview, VenueReview, UserCollection
├── venues/             # Venues, reservations, availability, dashboard
├── web/                # Home, mission, contact, error handlers
├── templates/          # HTML templates
├── static/             # CSS, JS (game_picker.js, event_form_venue.js, …)
└── media/              # Uploads (avatars, venue images) — runtime
```

## Frontend assets

| File | Purpose |
|------|---------|
| `static/js/game_picker.js` | BGG search UI, multi-select, recommended section |
| `static/js/event_form_venue.js` | Venue slot picker, catalog restriction, refresh recommended on venue change |
| `static/css/venues.css` | Partner venues hub styling |
| `static/css/game_picker.css` | Game picker panel styling |
| `static/css/custom.css` | Global theme, nav, event/venue cards |
