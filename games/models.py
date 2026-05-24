from django.db import models
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
)


def bgg_thing_url(bgg_id: int) -> str:
    return f"https://boardgamegeek.com/boardgame/{bgg_id}"


class BoardGame(models.Model):
    bgg_id = models.PositiveIntegerField(unique=True, db_index=True)
    title = models.CharField(max_length=300)
    year_published = models.PositiveSmallIntegerField(null=True, blank=True)
    min_players = models.IntegerField(
        validators=[MinValueValidator(1)],
        default=1,
    )
    max_players = models.IntegerField(
        validators=[MaxValueValidator(100)],
        default=4,
    )
    description = models.TextField(blank=True, default="")
    image_url = models.URLField(max_length=500, blank=True, default="")
    bgg_url = models.URLField(max_length=500, blank=True, default="")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.bgg_url and self.bgg_id:
            self.bgg_url = bgg_thing_url(self.bgg_id)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["title"]
