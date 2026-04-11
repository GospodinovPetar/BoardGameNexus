from django.contrib import admin
from django.db.models import Avg, FloatField, Value
from django.db.models.functions import Coalesce

from games.models import BoardGame, Genre


@admin.register(BoardGame)
class BoardGameAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "genre",
        "release_date",
        "review_avg_display",
        "min_players",
        "max_players",
        "image_url",
    )
    list_filter = ("genre", "release_date", "min_players", "max_players")
    search_fields = ("title", "description", "genre__name")
    ordering = ("title",)

    @admin.display(description="Avg. from reviews", ordering="review_avg")
    def review_avg_display(self, obj):
        value = getattr(obj, "review_avg", None)
        if value is None:
            return "0.0"
        return f"{float(value):.1f}"

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            review_avg=Coalesce(
                Avg("reviews__rating"),
                Value(0.0),
                output_field=FloatField(),
            ),
        )


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
