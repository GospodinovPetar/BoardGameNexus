from django.contrib import admin
from games.models import BoardGame, Genre


@admin.register(BoardGame)
class BoardGameAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "genre",
        "release_date",
        "rating",
        "min_players",
        "max_players",
        "image_url",
    )
    list_filter = ("genre", "release_date", "rating", "min_players", "max_players")
    search_fields = ("title", "description", "genre__name")
    ordering = ("title",)


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
