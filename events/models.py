from django.db import models
from events.validators import validate_future_date
from games.models import BoardGame
from django.core.validators import MinValueValidator

class Event(models.Model):
    name = models.CharField(
        max_length=100,
    )

    description = models.TextField()
    date_time = models.DateTimeField(
        validators=[validate_future_date],
    )

    location = models.CharField(
        max_length=200,
    )

    organizer_name = models.CharField(
        max_length=100,
    )

    current_players = models.PositiveIntegerField(
        default=1,
        verbose_name="Текущ брой играчи"
    )

    max_players = models.PositiveIntegerField(
        default=4,
        validators=[MinValueValidator(2)],
        verbose_name="Максимален брой места"
    )

    games = models.ManyToManyField(
        to=BoardGame,
        related_name='events',
    )

    def __str__(self):
        return self.name

    def has_free_spots(self):
        return self.current_players < self.max_players

    class Meta:
        ordering = ['date_time', 'name']
