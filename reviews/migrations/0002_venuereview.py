import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reviews", "0001_initial"),
        ("venues", "0003_venue_tables_working_hours_reservation_refactor"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="VenueReview",
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
                ("title", models.CharField(max_length=200)),
                ("content", models.TextField()),
                (
                    "rating",
                    models.PositiveSmallIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(5),
                        ]
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "author",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="venue_reviews",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "venue",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reviews",
                        to="venues.venue",
                    ),
                ),
            ],
            options={
                "verbose_name": "Venue review",
                "verbose_name_plural": "Venue reviews",
                "ordering": ["-created_at"],
                "unique_together": {("venue", "author")},
            },
        ),
    ]
