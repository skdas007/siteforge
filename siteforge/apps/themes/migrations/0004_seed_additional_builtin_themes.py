from django.db import migrations


def seed_more_themes(apps, schema_editor):
    Theme = apps.get_model("themes", "Theme")
    rows = [
        ("Black Red (bold contrast)", "blackred"),
        ("Emerald Gold (premium)", "emeraldgold"),
    ]
    for name, slug in rows:
        Theme.objects.update_or_create(
            slug=slug,
            defaults={"name": name, "is_active": True},
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("themes", "0003_seed_builtin_themes"),
    ]

    operations = [
        migrations.RunPython(seed_more_themes, noop_reverse),
    ]
