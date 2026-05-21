# Generated manually for venues app

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("events", "0002_event_organizer_eventregistration"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Venue",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=200)),
                ("slug", models.SlugField(max_length=220, unique=True)),
                ("description", models.TextField(blank=True, default="")),
                ("address", models.CharField(max_length=300)),
                ("city", models.CharField(max_length=100)),
                ("phone", models.CharField(blank=True, default="", max_length=50)),
                ("email", models.EmailField(blank=True, default="", max_length=254)),
                ("website", models.URLField(blank=True, default="")),
                (
                    "capacity",
                    models.PositiveIntegerField(
                        default=20,
                        validators=[django.core.validators.MinValueValidator(1)],
                    ),
                ),
                ("opening_hours", models.TextField(blank=True, default="")),
                (
                    "image",
                    models.ImageField(blank=True, null=True, upload_to="venues/"),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "staff",
                    models.ManyToManyField(
                        blank=True,
                        related_name="managed_venues",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="VenueReservation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("approved", "Approved"),
                            ("declined", "Declined"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("staff_response", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                (
                    "event",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="venue_reservation",
                        to="events.event",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="venue_reservations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "venue",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reservations",
                        to="venues.venue",
                    ),
                ),
            ],
            options={
                "ordering": ["-event__date_time"],
            },
        ),
    ]
