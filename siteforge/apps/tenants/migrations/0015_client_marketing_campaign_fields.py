from django.db import migrations, models
import apps.core.validators


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0014_legalpage"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="announcement_bg_color",
            field=models.CharField(blank=True, default="#0d6efd", max_length=7),
        ),
        migrations.AddField(
            model_name="client",
            name="announcement_cta_label",
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name="client",
            name="announcement_cta_url",
            field=models.URLField(blank=True, max_length=800),
        ),
        migrations.AddField(
            model_name="client",
            name="announcement_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="client",
            name="announcement_text",
            field=models.CharField(blank=True, max_length=240),
        ),
        migrations.AddField(
            model_name="client",
            name="announcement_text_color",
            field=models.CharField(blank=True, default="#ffffff", max_length=7),
        ),
        migrations.AddField(
            model_name="client",
            name="popup_clicks",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="client",
            name="popup_closes",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="client",
            name="popup_cta_label",
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name="client",
            name="popup_cta_url",
            field=models.URLField(blank=True, max_length=800),
        ),
        migrations.AddField(
            model_name="client",
            name="popup_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="client",
            name="popup_end_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="client",
            name="popup_image",
            field=models.ImageField(
                blank=True,
                help_text="Optional campaign popup image. Max 3 MB.",
                null=True,
                upload_to="tenants/popup/",
                validators=[apps.core.validators.validate_image_upload_size],
            ),
        ),
        migrations.AddField(
            model_name="client",
            name="popup_impressions",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="client",
            name="popup_message",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="client",
            name="popup_show_rule",
            field=models.CharField(
                blank=True,
                choices=[
                    ("always", "Show every page load"),
                    ("session", "Once per browser session"),
                    ("day", "Once per day"),
                ],
                default="session",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="client",
            name="popup_start_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="client",
            name="popup_title",
            field=models.CharField(blank=True, max_length=160),
        ),
    ]
