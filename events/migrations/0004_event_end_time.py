from datetime import timedelta

from django.db import migrations, models


def backfill_end_time(apps, schema_editor):
    Event = apps.get_model("events", "Event")
    for event in Event.objects.filter(end_time__isnull=True):
        event.end_time = event.date_time + timedelta(hours=2)
        event.save(update_fields=["end_time"])


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0003_event_venue"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="end_time",
            field=models.DateTimeField(null=True),
        ),
        migrations.RunPython(backfill_end_time, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="event",
            name="end_time",
            field=models.DateTimeField(),
        ),
    ]
