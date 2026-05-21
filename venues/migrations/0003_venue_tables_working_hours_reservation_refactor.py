from datetime import time

from django.db import migrations, models
import django.core.validators


def migrate_reservation_statuses(apps, schema_editor):
    VenueReservation = apps.get_model("venues", "VenueReservation")
    for reservation in VenueReservation.objects.all():
        if reservation.staff_response and not reservation.staff_note:
            reservation.staff_note = reservation.staff_response
        if reservation.status in ("approved", "pending"):
            reservation.status = "confirmed"
        elif reservation.status == "declined":
            reservation.status = "cancelled"
        reservation.save(update_fields=["status", "staff_note"])


class Migration(migrations.Migration):

    dependencies = [
        ("venues", "0002_venue_hourly_rate_games"),
    ]

    operations = [
        migrations.AddField(
            model_name="venue",
            name="opens_at",
            field=models.TimeField(default=time(10, 0)),
        ),
        migrations.AddField(
            model_name="venue",
            name="closes_at",
            field=models.TimeField(default=time(22, 0)),
        ),
        migrations.AddField(
            model_name="venue",
            name="table_count",
            field=models.PositiveIntegerField(
                default=6,
                validators=[django.core.validators.MinValueValidator(1)],
                help_text="Number of reservable tables.",
            ),
        ),
        migrations.RemoveField(
            model_name="venue",
            name="opening_hours",
        ),
        migrations.AddField(
            model_name="venuereservation",
            name="tables_reserved",
            field=models.PositiveIntegerField(
                default=1,
                validators=[django.core.validators.MinValueValidator(1)],
            ),
        ),
        migrations.AddField(
            model_name="venuereservation",
            name="staff_note",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="venuereservation",
            name="cancelled_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(migrate_reservation_statuses, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="venuereservation",
            name="staff_response",
        ),
        migrations.RemoveField(
            model_name="venuereservation",
            name="responded_at",
        ),
        migrations.AlterField(
            model_name="venuereservation",
            name="status",
            field=models.CharField(
                choices=[
                    ("confirmed", "Confirmed"),
                    ("cancelled", "Cancelled"),
                ],
                default="confirmed",
                max_length=20,
            ),
        ),
    ]
