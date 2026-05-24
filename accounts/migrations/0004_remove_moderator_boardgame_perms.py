from django.db import migrations


def remove_moderator_boardgame_perms(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    try:
        moderators = Group.objects.get(name="Moderators")
    except Group.DoesNotExist:
        return
    codenames = ("add_boardgame", "change_boardgame", "delete_boardgame")
    for codename in codenames:
        perms = Permission.objects.filter(
            codename=codename,
            content_type__app_label="games",
            content_type__model="boardgame",
        )
        for perm in perms:
            moderators.permissions.remove(perm)


def restore_moderator_boardgame_perms(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    try:
        moderators = Group.objects.get(name="Moderators")
    except Group.DoesNotExist:
        return
    codenames = ("add_boardgame", "change_boardgame", "delete_boardgame")
    for codename in codenames:
        perms = Permission.objects.filter(
            codename=codename,
            content_type__app_label="games",
            content_type__model="boardgame",
        )
        for perm in perms:
            moderators.permissions.add(perm)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_customuser_no_show_strikes"),
        ("games", "0003_bgg_cache_refactor"),
    ]

    operations = [
        migrations.RunPython(
            remove_moderator_boardgame_perms,
            restore_moderator_boardgame_perms,
        ),
    ]
