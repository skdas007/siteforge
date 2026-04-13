from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0008_client_favicon"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="map_embed_url",
            field=models.URLField(
                blank=True,
                help_text="Optional map embed URL for Contact section iframe (Google Maps / OpenStreetMap embed link).",
                max_length=1200,
            ),
        ),
    ]
