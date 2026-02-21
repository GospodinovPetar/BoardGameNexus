from django import template

register = template.Library()


@register.filter
def is_event_full(event):
    return event.current_players >= event.max_players


@register.filter
def player_range(game):
    return f"{game.min_players} - {game.max_players} players"
