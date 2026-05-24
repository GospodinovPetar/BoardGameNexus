from django.db import migrations, models
import django.core.validators


def wipe_games_and_genres(apps, schema_editor):
    BoardGame = apps.get_model("games", "BoardGame")
    Genre = apps.get_model("games", "Genre")
    connection = schema_editor.connection
    m2m_tables = (
        "events_event_games",
        "venues_venue_games",
    )
    with connection.cursor() as cursor:
        for table in m2m_tables:
            cursor.execute(
                """
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = %s
                """,
                [table],
            )
            if cursor.fetchone():
                cursor.execute(f'DELETE FROM "{table}"')
        for table in ("reviews_gamereview", "reviews_usercollection"):
            cursor.execute(
                """
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = %s
                """,
                [table],
            )
            if cursor.fetchone():
                cursor.execute(f'DELETE FROM "{table}"')
    BoardGame.objects.all().delete()
    Genre.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0002_boardgame_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="boardgame",
            name="bgg_id",
            field=models.PositiveIntegerField(db_index=True, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="boardgame",
            name="year_published",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="boardgame",
            name="bgg_url",
            field=models.URLField(blank=True, default="", max_length=500),
        ),
        migrations.RunPython(wipe_games_and_genres, migrations.RunPython.noop),
        migrations.RemoveField(model_name="boardgame", name="genre"),
        migrations.RemoveField(model_name="boardgame", name="release_date"),
        migrations.RemoveField(model_name="boardgame", name="image"),
        migrations.AlterField(
            model_name="boardgame",
            name="title",
            field=models.CharField(max_length=300),
        ),
        migrations.AlterField(
            model_name="boardgame",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="boardgame",
            name="image_url",
            field=models.URLField(blank=True, default="", max_length=500),
        ),
        migrations.AlterField(
            model_name="boardgame",
            name="min_players",
            field=models.IntegerField(
                default=1,
                validators=[django.core.validators.MinValueValidator(1)],
            ),
        ),
        migrations.AlterField(
            model_name="boardgame",
            name="max_players",
            field=models.IntegerField(
                default=4,
                validators=[django.core.validators.MaxValueValidator(100)],
            ),
        ),
        migrations.AlterField(
            model_name="boardgame",
            name="bgg_id",
            field=models.PositiveIntegerField(db_index=True, unique=True),
        ),
        migrations.DeleteModel(name="Genre"),
    ]
