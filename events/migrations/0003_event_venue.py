# Generated manually for Event.venue

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("venues", "0001_initial"),
        ("events", "0002_event_organizer_eventregistration"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="venue",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="events",
                to="venues.venue",
            ),
        ),
    ]
