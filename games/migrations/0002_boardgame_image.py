from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("games", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="boardgame",
            name="image",
            field=models.ImageField(blank=True, null=True, upload_to="games/"),
        ),
    ]

