from django.db import models
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
)


class Genre(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class BoardGame(models.Model):
    title = models.CharField(
        max_length=200,
        unique=True,
    )
    genre = models.ForeignKey(
        to=Genre,
        on_delete=models.CASCADE,
    )
    release_date = models.DateField(
        null=True,
        blank=True,
    )
    rating = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(5.0),
        ],
    )
    min_players = models.IntegerField(
        validators=[
            MinValueValidator(1),
        ]
    )
    max_players = models.IntegerField(
        validators=[
            MaxValueValidator(100),
        ]
    )
    description = models.TextField(
        blank=True,
        null=True,
    )
    image_url = models.URLField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["title"]
