from django.contrib import admin

from games.models import BoardGame


@admin.register(BoardGame)
class BoardGameAdmin(admin.ModelAdmin):
    list_display = ("title", "bgg_id", "year_published", "min_players", "max_players")
    search_fields = ("title", "bgg_id")
    readonly_fields = (
        "bgg_id",
        "title",
        "year_published",
        "min_players",
        "max_players",
        "description",
        "image_url",
        "bgg_url",
    )
    ordering = ("title",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
