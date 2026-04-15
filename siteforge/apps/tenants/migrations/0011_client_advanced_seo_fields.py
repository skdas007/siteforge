from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0009_client_map_embed_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="seo_address_country",
            field=models.CharField(blank=True, default="IN", max_length=10),
        ),
        migrations.AddField(
            model_name="client",
            name="seo_address_locality",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="client",
            name="seo_address_region",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="client",
            name="seo_author",
            field=models.CharField(blank=True, help_text="Optional author/brand meta tag.", max_length=200),
        ),
        migrations.AddField(
            model_name="client",
            name="seo_founder",
            field=models.CharField(blank=True, help_text="Founder name for Organization schema.", max_length=120),
        ),
        migrations.AddField(
            model_name="client",
            name="seo_geo_placename",
            field=models.CharField(blank=True, help_text="Example: Bhuban, Odisha", max_length=120),
        ),
        migrations.AddField(
            model_name="client",
            name="seo_geo_position",
            field=models.CharField(blank=True, help_text="Example: 20.881;85.833", max_length=50),
        ),
        migrations.AddField(
            model_name="client",
            name="seo_geo_region",
            field=models.CharField(blank=True, help_text="Example: IN-OD", max_length=24),
        ),
        migrations.AddField(
            model_name="client",
            name="seo_icbm",
            field=models.CharField(blank=True, help_text="Example: 20.881,85.833", max_length=50),
        ),
        migrations.AddField(
            model_name="client",
            name="seo_keywords",
            field=models.TextField(blank=True, help_text="Optional comma-separated keywords for search engines."),
        ),
        migrations.AddField(
            model_name="client",
            name="seo_language",
            field=models.CharField(blank=True, default="English", max_length=40),
        ),
        migrations.AddField(
            model_name="client",
            name="seo_postal_code",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="client",
            name="seo_revisit_after",
            field=models.CharField(blank=True, default="7 days", max_length=40),
        ),
        migrations.AddField(
            model_name="client",
            name="seo_robots",
            field=models.CharField(blank=True, default="index, follow", help_text="Robots directive, e.g. index, follow", max_length=40),
        ),
    ]
