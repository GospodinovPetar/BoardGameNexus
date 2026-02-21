# BoardGame Nexus

A web app for board game fans - browse games, create events, and keep track of who's joining. Built with Django as my exam project for the SoftUni Django Basics course.

---

## What it does

The app has three main sections:

**Games** - a catalog where you can add board games with ratings, player counts, genre, and a cover image. The list has search and filtering (by genre, rating range, player count, release date) and sorting.

**Events** - create gaming events, set a date/time and location, link them to games from the catalog, and track how many players have joined. Events can be filtered and sorted as well.

**Static pages** - The Contact page. The home and mission pages show live counts of games and events in the database.

A small extra I liked: when you open "Create Event" from a game's detail page, that game gets pre-selected in the event form automatically.

---

## Tech

- Django 6.0.2
- PostgreSQL
- Bootstrap 5 (dark theme)
- django-crispy-forms + crispy-bootstrap5
- django-jazzmin (admin panel)
- python-dotenv

---

## Setup

**Requirements:** Python 3.10+, PostgreSQL

```bash
git clone https://github.com/your-username/BoardGameNexus.git
cd BoardGameNexus

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` file in the project root (same folder as `manage.py`):

```
SECRET_KEY=your-secret-key-here
DB_NAME=your_database_name
DB_USER=your_postgres_username
DB_PASSWORD=your_postgres_password
DB_HOST=127.0.0.1
DB_PORT=5432
```

```bash
python manage.py migrate
python manage.py createsuperuser   # for admin access
python manage.py runserver
```

App runs at `http://127.0.0.1:8000/`

---

## Pages

| URL | Page |
|---|---|
| `/` | Home |
| `/mission/` | Our Mission |
| `/contact/` | Contact |
| `/games/` | All games (search + filter) |
| `/games/details/<id>` | Game detail |
| `/games/add/` | Add game |
| `/games/edit/<id>` | Edit game |
| `/games/delete/<id>` | Delete game (with confirmation) |
| `/events/` | All events (search + filter) |
| `/events/<id>/` | Event detail |
| `/events/add/` | Create event |
| `/events/edit/<id>` | Edit event |
| `/events/delete/<id>` | Delete event (with confirmation) |
| `/events/join/<id>/` | Join event |
| `/admin/` | Admin panel (superuser only) |

---

## Forms and validation

`GameForm` validates that min_players =< max_players, rating is between 0 and 5, and release date isn't in the future. `EventForm` validates that current_players =< max_players and the event date isn't in the past - this is also enforced at the model level with a custom validator (`validate_future_date`). Both delete forms render all fields as read-only so you can review what you're deleting before confirming.

---

## Templates

All pages extend `base.html`. Create/Edit/Delete for both games and events share a single `_form_card.html` partial - it handles the form layout, cancel button, and submit button color (red for delete, blue otherwise) based on context variables.

Custom template filters are in `games/templatetags/game_filters.py`:
- `player_range` - formats min/max players as "2 - 4 players", used in game cards and detail page
- `is_event_full` - returns True if an event has no free spots, used to show a "Full" badge on event cards

---

## Project structure

```
BoardGameNexus/
├── games/          # Game catalog - models, views, forms, custom template filters
├── events/         # Event management - includes session-based join tracking
├── web/            # Static pages (home, mission, contact)
├── templates/      # All HTML templates
├── static/         # CSS and images
└── BoardGameNexus/ # Project settings and URLs
```

Three apps, three models (`Genre`, `BoardGame`, `Event`), many-to-one and many-to-many relationships between them.

---

## Notes

- The custom 404 page only shows when `DEBUG = False`
- Session tracking for joined events resets if you clear browser cookies
- Tested on Python 3.12 / macOS
