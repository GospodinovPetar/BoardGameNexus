from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from events.validators import validate_future_date
from games.models import BoardGame
from venues.utils import build_google_maps_url


class Event(models.Model):
    name = models.CharField(
        max_length=100,
    )

    description = models.TextField()
    date_time = models.DateTimeField(
        validators=[validate_future_date],
    )
    end_time = models.DateTimeField()

    location = models.CharField(
        max_length=200,
    )

    venue = models.ForeignKey(
        "venues.Venue",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )

    organizer_name = models.CharField(
        max_length=100,
    )

    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="organized_events",
    )

    current_players = models.PositiveIntegerField(
        default=1, verbose_name="Current Players"
    )

    max_players = models.PositiveIntegerField(
        default=4,
        validators=[MinValueValidator(2)],
        verbose_name="Expected players",
    )

    games = models.ManyToManyField(
        to=BoardGame,
        related_name="events",
    )

    def __str__(self):
        return self.name

    @property
    def display_location(self):
        if self.venue_id:
            return self.venue.display_location()
        return self.location

    @property
    def maps_address(self):
        if self.venue_id:
            return self.venue.full_address
        return self.location

    @property
    def google_maps_url(self):
        return build_google_maps_url(self.maps_address)

    @property
    def duration_hours(self):
        if not self.end_time or not self.date_time:
            return Decimal("0")
        delta = self.end_time - self.date_time
        hours = Decimal(str(delta.total_seconds())) / Decimal("3600")
        return max(hours, Decimal("0"))

    def confirmed_participant_count(self):
        return self.active_registration_count()

    @property
    def venue_total_price(self):
        if not self.venue_id or not self.venue.hourly_rate:
            return None
        return (self.venue.hourly_rate * self.duration_hours).quantize(Decimal("0.01"))

    @property
    def venue_price_per_person(self):
        total = self.venue_total_price
        if total is None:
            return None
        count = max(self.confirmed_participant_count(), 1)
        return (total / Decimal(count)).quantize(Decimal("0.01"))

    def has_free_spots(self):
        return self.current_players < self.max_players

    def active_registration_count(self):
        return self.registrations.filter(
            status__in=[
                EventRegistration.STATUS_REGISTERED,
                EventRegistration.STATUS_PRESENT,
            ]
        ).count()

    def attendance_window_open(self):
        """True during [event start, event start + 1 hour]."""
        now = timezone.now()
        return self.date_time <= now <= self.date_time + timezone.timedelta(hours=1)

    def attendance_window_closed(self):
        """True once more than 1 hour has passed since event start."""
        return timezone.now() > self.date_time + timezone.timedelta(hours=1)

    class Meta:
        ordering = ["date_time", "name"]


class EventRegistration(models.Model):
    STATUS_REGISTERED = "registered"
    STATUS_PRESENT = "present"
    STATUS_REMOVED = "removed"
    STATUS_NO_SHOW = "no_show"

    STATUS_CHOICES = [
        (STATUS_REGISTERED, "Registered"),
        (STATUS_PRESENT, "Present"),
        (STATUS_REMOVED, "Removed"),
        (STATUS_NO_SHOW, "No Show"),
    ]

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="registrations",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="event_registrations",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_REGISTERED,
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    marked_present_at = models.DateTimeField(null=True, blank=True)
    removed_at = models.DateTimeField(null=True, blank=True)
    no_show_marked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("event", "user")
        ordering = ["joined_at"]

    def __str__(self):
        return f"{self.user.username} → {self.event.name} ({self.status})"
