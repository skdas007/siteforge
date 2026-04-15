from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0011_client_advanced_seo_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="address_text",
            field=models.TextField(blank=True, help_text="Business address shown in footer/contact sections."),
        ),
        migrations.AddField(
            model_name="client",
            name="facebook_url",
            field=models.URLField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="client",
            name="instagram_url",
            field=models.URLField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="client",
            name="youtube_url",
            field=models.URLField(blank=True, max_length=500),
        ),
    ]
