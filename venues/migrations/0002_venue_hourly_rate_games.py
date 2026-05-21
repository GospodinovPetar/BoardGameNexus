import django.core.validators
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0002_boardgame_image"),
        ("venues", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="venue",
            name="hourly_rate",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                help_text="Price per hour for venue reservation (BGN).",
                max_digits=8,
                validators=[django.core.validators.MinValueValidator(Decimal("0"))],
            ),
        ),
        migrations.AddField(
            model_name="venue",
            name="games",
            field=models.ManyToManyField(
                blank=True,
                related_name="venues",
                to="games.boardgame",
            ),
        ),
    ]
