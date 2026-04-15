from django.contrib import admin

from games.models import BoardGame, Genre


@admin.register(BoardGame)
class BoardGameAdmin(admin.ModelAdmin):
    list_display = ("title", "genre", "release_date", "min_players", "max_players")
    list_filter = ("genre",)
    search_fields = ("title", "description")
    ordering = ("title",)


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    search_fields = ("name",)
