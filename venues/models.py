from datetime import datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from games.models import BoardGame
from venues.utils import build_google_maps_url


class Venue(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True, default="")
    address = models.CharField(max_length=300)
    city = models.CharField(max_length=100)
    phone = models.CharField(max_length=50, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    website = models.URLField(blank=True, default="")
    capacity = models.PositiveIntegerField(
        default=20,
        validators=[MinValueValidator(1)],
        help_text="Total guest capacity (informational).",
    )
    table_count = models.PositiveIntegerField(
        default=6,
        validators=[MinValueValidator(1)],
        help_text="Number of reservable tables.",
    )
    hourly_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Price per hour for venue reservation (BGN).",
    )
    opens_at = models.TimeField(default=time(10, 0))
    closes_at = models.TimeField(default=time(22, 0))
    image = models.ImageField(upload_to="venues/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    staff = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="managed_venues",
        blank=True,
    )
    games = models.ManyToManyField(
        BoardGame,
        related_name="venues",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "venue"
            slug = base_slug
            counter = 1
            while Venue.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def full_address(self):
        return f"{self.address}, {self.city}"

    def display_location(self):
        return self.full_address

    @property
    def google_maps_url(self):
        return build_google_maps_url(self.full_address)

    @property
    def working_hours_display(self):
        return f"{self.opens_at.strftime('%H:%M')} – {self.closes_at.strftime('%H:%M')}"

    def iter_hour_slot_starts(self, on_date):
        """Yield aware datetimes for each bookable hour start on on_date."""
        tz = timezone.get_current_timezone()
        start_dt = timezone.make_aware(datetime.combine(on_date, self.opens_at), tz)
        close_dt = timezone.make_aware(datetime.combine(on_date, self.closes_at), tz)
        slot = start_dt
        while slot + timedelta(hours=1) <= close_dt:
            yield slot
            slot += timedelta(hours=1)


class VenueReservation(models.Model):
    STATUS_CONFIRMED = "confirmed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    venue = models.ForeignKey(
        Venue,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    event = models.OneToOneField(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="venue_reservation",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="venue_reservations",
    )
    tables_reserved = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_CONFIRMED,
    )
    staff_note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-event__date_time"]

    def __str__(self):
        return f"{self.venue.name} — {self.event.name} ({self.status})"

    @property
    def party_size(self):
        return self.event.confirmed_participant_count()
