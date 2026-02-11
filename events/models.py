from django.db import models
from events.validators import validate_future_date
from games.models import BoardGame

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
    organizer_email = models.EmailField()
    games = models.ManyToManyField(
        to=BoardGame,
        related_name='events',
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['date_time', 'name']
