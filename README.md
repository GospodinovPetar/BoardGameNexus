# 🎲 BoardGame Nexus

> **Your central hub for everything board games.**  
> Discover new titles, organize events, and connect with fellow enthusiasts - all in one place.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Database Design](#database-design)
- [Templates & Pages](#templates--pages)
- [Forms & Validation](#forms--validation)
- [Custom Template Filters](#custom-template-filters)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Usage](#usage)

---

## Overview

BoardGame Nexus is a Django web application built as part of the **Django Basics Course @ SoftUni**. It allows users to browse a catalog of board games, manage gaming events, and explore community gatherings - without requiring login or registration.

---

## Features

- 🎮 **Game Catalog** - Browse, search, filter, and sort board games by title, genre, rating, player count, and release date
- 📅 **Event Management** - Create, join, edit, and delete gaming events with player capacity tracking
- 🔍 **Advanced Filtering** - Multi-field search with collapsible filter panels on both Games and Events pages
- ✅ **Full CRUD** - Complete Create, Read, Update, Delete functionality for both Games and Events
- 🚫 **Delete Confirmation** - Confirmation step with read-only form fields before any deletion
- 📢 **In-App Notifications** - Django messages framework used for success, warning, and error feedback
- 🎨 **Responsive Design** - Bootstrap 5 dark theme, mobile-friendly layout
- 🛡️ **Custom 404 Page** - Friendly error page for missing routes
- ⚙️ **Jazzmin Admin Panel** - Enhanced Django admin interface

---

## Tech Stack

| Technology | Purpose |
|---|---|
| **Django 6.0.2** | Web framework |
| **Python 3.12** | Programming language |
| **PostgreSQL** | Database |
| **Bootstrap 5.3** | Frontend styling (dark theme) |
| **Bootstrap Icons** | Icon library |
| **django-crispy-forms** | Form rendering |
| **crispy-bootstrap5** | Bootstrap 5 crispy forms template pack |
| **django-jazzmin** | Admin panel customization |
| **python-dotenv** | Environment variable management |

---

## Database Design

### Models

**`Genre`** *(games app)*
| Field | Type | Notes |
|---|---|---|
| `name` | CharField | unique |

**`BoardGame`** *(games app)*
| Field | Type | Notes |
|---|---|---|
| `title` | CharField | unique |
| `genre` | ForeignKey → Genre | **many-to-one** relationship, CASCADE |
| `release_date` | DateField | optional |
| `rating` | FloatField | 0.0 – 5.0, validated |
| `min_players` | IntegerField | min 1 |
| `max_players` | IntegerField | max 100 |
| `description` | TextField | optional |
| `image_url` | URLField | optional |

**`Event`** *(events app)*
| Field | Type | Notes |
|---|---|---|
| `name` | CharField | — |
| `description` | TextField | — |
| `date_time` | DateTimeField | must be in the future |
| `location` | CharField | — |
| `organizer_name` | CharField | — |
| `current_players` | PositiveIntegerField | default 1 |
| `max_players` | PositiveIntegerField | min 2 |
| `games` | ManyToManyField → BoardGame | **many-to-many** relationship |

### Relationships
- `BoardGame` → `Genre` : **Many-to-One** (ForeignKey)
- `Event` ↔ `BoardGame` : **Many-to-Many** (ManyToManyField)

---

## Templates & Pages

| Template | Dynamic Data | Description                                       |
|---|--------------|---------------------------------------------------|
| `base.html` | -            | Base layout - navbar, footer, messages            |
| `_form_card.html` | -            | Reusable partial - shared by game_cud & event_cud |
| `home.html` | ✅            | Live game & event counts                          |
| `mission.html` | ✅            | Mission page with live counts                     |
| `contact.html` | -            | Contact information                               |
| `games.html` | ✅            | All games - filterable, sortable                  |
| `game_detail.html` | ✅            | Single game details                               |
| `game_cud.html` | ✅            | Create / Edit / Delete game form                  |
| `events.html` | ✅            | All events - filterable, sortable                 |
| `event_detail.html` | ✅            | Single event details                              |
| `event_cud.html` | ✅            | Create / Edit / Delete event form                 |
| `404.html` | -            | Custom 404 error page                             |

**Template inheritance:** All pages extend `base.html`. The `_form_card.html` partial is reused across `game_cud.html` and `event_cud.html`, avoiding code duplication.

---

## Forms & Validation

| Form | Type | Key Validations                                                               |
|---|---|-------------------------------------------------------------------------------|
| `GameForm` | ModelForm | `min_players` ≤ `max_players`, rating 0–5, release date not in the future     |
| `GameSearchForm` | Form | Optional filters - title, genre, rating range, player range, date range       |
| `EventForm` | ModelForm | `current_players` ≤ `max_players`, date must be in the future                 |
| `EventSearchForm` | Form | Optional filters - name, organizer, location, player range, date range, games |

**Additional validation features:**
- Validations applied both in **forms** (`clean()`) and **models** (field validators + `validate_future_date`)
- User-friendly, localized error messages on all fields
- Customized labels, placeholders, and help texts throughout
- Delete views render forms with **read-only fields** to prevent accidental edits
- All delete operations require an explicit **confirmation step**

---

## Custom Template Filters

Located in `games/templatetags/game_filters.py`:

```python
# Returns True if the event has no free spots
# Usage: {% if event|is_event_full %}
@register.filter
def is_event_full(event):
    return event.current_players >= event.max_players

# Returns a formatted player range string
# Usage: {{ game|player_range }} → "2 - 4 players"
@register.filter
def player_range(game):
    return f"{game.min_players} - {game.max_players} players"
```

**Used in templates:**
- `events.html` - `is_event_full` renders a red "Full" badge on fully booked events
- `games.html` - `player_range` formats the player count in game cards
- `game_detail.html` - `player_range` formats the player count in the detail view

---

## Getting Started

### Prerequisites

- Python 3.10+
- pip
- PostgreSQL server running locally

### Installation

**1. Clone the repository:**
```bash
git clone https://github.com/your-username/BoardGameNexus.git
cd BoardGameNexus
```

**2. Create and activate a virtual environment:**
```bash
python -m venv .venv

# macOS / Linux:
source .venv/bin/activate

# Windows:
.venv\Scripts\activate
```

**3. Install dependencies:**
```bash
pip install -r requirements.txt
```

**4. Set up environment variables:**

Create a `.env` file in the project root (same folder as `manage.py`) with the following content:

```env
SECRET_KEY=your-secret-key-here
DB_NAME=your_database_name
DB_USER=your_postgres_username
DB_PASSWORD=your_postgres_password
DB_HOST=127.0.0.1
DB_PORT=5432
```

> See [Environment Variables](#environment-variables) below for details on each variable.

**5. Create the PostgreSQL database:**
```sql
CREATE DATABASE your_database_name;
```

**6. Apply migrations:**
```bash
python manage.py migrate
```

**7. Create a superuser** *(for admin panel access)*:
```bash
python manage.py createsuperuser
```

**8. Run the development server:**
```bash
python manage.py runserver
```

The application will be available at **http://127.0.0.1:8000/**

---

## Environment Variables

All sensitive configuration is stored in a `.env` file. **This file is not committed to version control.**

| Variable | Description | Example |
|---|---|---|
| `SECRET_KEY` | Django secret key for cryptographic signing | `django-insecure-abc123...` |
| `DB_NAME` | PostgreSQL database name | `nexus` |
| `DB_USER` | PostgreSQL username | `postgres` |
| `DB_PASSWORD` | PostgreSQL password | `yourpassword` |
| `DB_HOST` | Database host | `127.0.0.1` |
| `DB_PORT` | Database port | `5432` |

---

## Usage

| Page | URL | Description                         |
|---|---|-------------------------------------|
| Home | `/` | Landing page with live stats        |
| Our Mission | `/mission/` | About the platform                  |
| Contact | `/contact/` | Contact information                 |
| All Games | `/games/` | Browse & filter the game catalog    |
| Game Detail | `/games/details/<id>` | Full info for a single game         |
| Add Game | `/games/add/` | Add a new game to the catalog       |
| Edit Game | `/games/edit/<id>` | Edit an existing game               |
| Delete Game | `/games/delete/<id>` | Delete a game (with confirmation)   |
| All Events | `/events/` | Browse & filter events              |
| Event Detail | `/events/<id>/` | Full info for a single event        |
| Join Event | `/events/join/<id>/` | Join an event (session-based)       |
| Add Event | `/events/add/` | Create a new event                  |
| Edit Event | `/events/edit/<id>` | Edit an existing event              |
| Delete Event | `/events/delete/<id>` | Delete an event (with confirmation) |
| Admin Panel | `/admin/` | Django admin - requires superuser   |

---

## License

This project is open-sourced under the **MIT License**.