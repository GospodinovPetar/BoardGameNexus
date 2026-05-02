from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_create_user_groups"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="no_show_strikes",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
