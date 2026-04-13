from django.db import migrations


def seed_builtin_themes(apps, schema_editor):
    Theme = apps.get_model("themes", "Theme")
    builtins = [
        ("Default", "default"),
        ("Minimal", "minimal"),
        ("Clarity (agency style + animations)", "clarity"),
        ("Aurora (colorful gradient)", "aurora"),
        ("Midnight (dark mode)", "midnight"),
    ]
    for name, slug in builtins:
        Theme.objects.update_or_create(
            slug=slug,
            defaults={"name": name, "is_active": True},
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("themes", "0002_add_upload_size_validators"),
    ]

    operations = [
        migrations.RunPython(seed_builtin_themes, noop_reverse),
    ]
