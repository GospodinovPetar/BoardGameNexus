# BoardGame Nexus

A Django web app for board game fans: browse a game catalog, create/join events, write reviews, and manage your personal collection. Includes a REST API with Swagger docs.

## Features

- **Games**: genre-based catalog of board games
- **Events**: create events, link them to games, and join events (with capacity limits)
- **Accounts**: custom user model + profile (bio/avatar/date of birth)
- **Reviews**: one review per user per game (1–5 rating)
- **Collections**: track games as “Want to Play / Currently Playing / Played / Owned”
- **API**: DRF endpoints for games, events, reviews, collections, and current user
- **API docs**: OpenAPI schema + Swagger UI

## Tech stack

- **Backend**: Django 6.0.2, Django REST Framework
- **DB**: PostgreSQL
- **UI**: Bootstrap 5, `django-crispy-forms` + `crispy-bootstrap5`
- **Admin**: `django-jazzmin`
- **API schema**: `drf-spectacular`
- **Config**: `python-dotenv` (loads `.env`)

## Quickstart

### Local development

**Requirements**: Python 3.10+ (tested with 3.12), PostgreSQL

```bash
cp .env.example .env

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata initial_data.json
python manage.py createsuperuser
python manage.py runserver
```

App runs at `http://127.0.0.1:8000/`

### Docker (Postgres + Django)

```bash
cp .env.example .env
docker compose up --build
```

`docker-compose.yml` starts Postgres + Django. The `web` service runs migrations and loads `initial_data.json` on startup, then serves Django on port 8000.

## Environment variables

The project reads config from `.env` (loaded via `python-dotenv`). Required variables:

- **`SECRET_KEY`**
- **`DB_NAME`**
- **`DB_USER`**
- **`DB_PASSWORD`**
- **`DB_HOST`** (local dev usually `127.0.0.1`; Docker Compose uses `db`)
- **`DB_PORT`** (usually `5432`)
- **`ALLOWED_HOSTS`** (optional, comma-separated; e.g. `localhost,127.0.0.1`)

## Key routes

### Web

| URL | Purpose |
|---|---|
| `/` | Home |
| `/mission/` | Mission |
| `/contact/` | Contact |
| `/games/` | Games list |
| `/games/details/<id>` | Game detail |
| `/games/add/` | Add game |
| `/games/edit/<id>` | Edit game |
| `/games/delete/<id>` | Delete game |
| `/events/` | Events list |
| `/events/<id>/` | Event detail |
| `/events/add/` | Create event |
| `/events/edit/<id>` | Edit event |
| `/events/delete/<id>` | Delete event |
| `/events/join/<id>/` | Join event |
| `/reviews/` | Reviews list |
| `/reviews/<id>/` | Review detail |
| `/reviews/game/<game_id>/create/` | Create review for a game |
| `/accounts/register/` | Register |
| `/accounts/login/` | Login |
| `/accounts/profile/` | Profile |
| `/admin/` | Admin |

### API

Base path is **`/api/`**.

| URL | Purpose |
|---|---|
| `/api/genres/` | List genres |
| `/api/games/` | List/create games |
| `/api/games/<id>/` | Retrieve/update/delete a game |
| `/api/events/` | List/create events |
| `/api/events/<id>/` | Retrieve/update/delete an event |
| `/api/reviews/` | List/create reviews |
| `/api/reviews/<id>/` | Retrieve/update/delete a review |
| `/api/collections/` | List/create current user’s collection entries |
| `/api/collections/<id>/` | Retrieve/update/delete one collection entry |
| `/api/users/me/` | Get/update the current user |
| `/api/auth/token/` | Obtain auth token (DRF token auth) |

API documentation:

- **OpenAPI schema**: `/api/schema/`
- **Swagger UI**: `/api/swagger/`

## Data / fixtures

`initial_data.json` is a fixture located under `games/fixtures/` and can be loaded with:

```bash
python manage.py loaddata initial_data.json
```

## Tests

```bash
python manage.py test
```

## Project structure

```
BoardGameNexus/
├── BoardGameNexus/  # Project settings/URLs
├── accounts/        # Custom user + profile, auth views
├── api/             # DRF API (endpoints, serializers, permissions)
├── events/          # Events
├── games/           # Games + genres
├── reviews/         # Reviews + collections
├── web/             # Static pages (home/mission/contact)
├── templates/       # HTML templates
├── static/          # Project-wide static files
└── media/           # Uploaded files (created at runtime)
```

## Notes

- **Custom 404** is shown only when `DEBUG = False`.
- **Docker Compose** uses defaults for DB credentials if not provided (see `docker-compose.yml`).
- Tested on **Python 3.12** / macOS.
