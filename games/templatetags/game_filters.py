from django import template
from urllib.parse import urlencode, parse_qs

register = template.Library()


@register.filter
def is_event_full(event):
    return event.current_players >= event.max_players


@register.filter
def player_range(game):
    return f"{game.min_players} - {game.max_players} players"


@register.filter
def dont_include_page(querystring, field):
    parsed = parse_qs(querystring)
    parsed.pop(field, None)
    return urlencode(parsed, doseq=True)
