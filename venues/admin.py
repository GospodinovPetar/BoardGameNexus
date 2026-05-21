from django.contrib import admin

from venues.models import Venue, VenueReservation


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "city",
        "table_count",
        "capacity",
        "hourly_rate",
        "opens_at",
        "closes_at",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "city")
    search_fields = ("name", "address", "city", "email")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("staff", "games")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("name", "slug", "description", "is_active", "image")}),
        ("Location", {"fields": ("address", "city", "phone", "email", "website")}),
        (
            "Booking",
            {
                "fields": (
                    "table_count",
                    "capacity",
                    "hourly_rate",
                    "opens_at",
                    "closes_at",
                ),
            },
        ),
        ("Staff & games", {"fields": ("staff", "games")}),
        ("Meta", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(VenueReservation)
class VenueReservationAdmin(admin.ModelAdmin):
    list_display = (
        "event",
        "venue",
        "requested_by",
        "tables_reserved",
        "status",
        "created_at",
        "cancelled_at",
    )
    list_filter = ("status", "venue")
    search_fields = ("event__name", "venue__name", "requested_by__username")
    readonly_fields = ("created_at", "updated_at", "cancelled_at")
    raw_id_fields = ("event", "requested_by")
