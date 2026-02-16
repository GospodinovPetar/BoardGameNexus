from django.contrib import admin
from events.models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "date_time",
        "location",
        "organizer_name",
        "current_players",
        "max_players",
        "has_free_spots",
    )
    list_filter = (
        "date_time",
        "location",
        "organizer_name",
        "current_players",
        "max_players",
        "games",
    )
    search_fields = ("name", "description", "location", "organizer_name")
    ordering = ("date_time", "name")
