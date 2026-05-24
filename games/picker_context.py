import json

from games.models import BoardGame


def games_to_picker_json(games) -> str:
    items = [
        {
            "id": g.pk,
            "bgg_id": g.bgg_id,
            "title": g.title,
            "image_url": g.image_url or "",
            "year_published": g.year_published,
        }
        for g in games
    ]
    return json.dumps(items)


def venue_games_to_picker_json(venue) -> str:
    if not venue:
        return "[]"
    return games_to_picker_json(venue.games.order_by("title"))


def resolve_picker_mode(venue) -> str:
    return "venue_catalog" if venue else "full"


def selected_games_from_form(form) -> list[BoardGame]:
    if form.instance and form.instance.pk:
        return list(form.instance.games.order_by("title"))
    initial = form.initial.get("games")
    if not initial:
        return []
    if initial and hasattr(initial[0], "pk"):
        return list(initial)
    return list(BoardGame.objects.filter(pk__in=initial))
