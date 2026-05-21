from django.contrib import admin

from events.models import Event, EventRegistration


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "date_time",
        "end_time",
        "location",
        "venue",
        "organizer_name",
        "organizer",
        "current_players",
        "max_players",
        "has_free_spots",
    )
    list_filter = (
        "date_time",
        "location",
        "venue",
        "organizer_name",
        "current_players",
        "max_players",
        "games",
    )
    search_fields = ("name", "description", "location", "organizer_name")
    ordering = ("date_time", "name")
    raw_id_fields = ("organizer", "venue")


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = (
        "event",
        "user",
        "status",
        "joined_at",
        "marked_present_at",
        "removed_at",
        "no_show_marked_at",
    )
    list_filter = ("status", "event")
    search_fields = ("event__name", "user__username")
    ordering = ("event", "joined_at")
    raw_id_fields = ("event", "user")
