# Generated manually for client SEO fields

import apps.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0006_add_upload_size_validators"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="seo_title",
            field=models.CharField(
                blank=True,
                help_text="Optional. Overrides the home page title for Google and social previews. If empty, hero title and business name are used.",
                max_length=200,
            ),
        ),
        migrations.AddField(
            model_name="client",
            name="seo_description",
            field=models.TextField(
                blank=True,
                help_text="Optional. Default description for your home page and product listing when you do not set a product-specific description. Aim for under ~160 characters.",
            ),
        ),
        migrations.AddField(
            model_name="client",
            name="seo_image",
            field=models.ImageField(
                blank=True,
                help_text="Optional. Default image when sharing your site (WhatsApp, Facebook, etc.). Recommended ~1200×630 px. Max 3 MB.",
                null=True,
                upload_to="tenants/seo/",
                validators=[apps.core.validators.validate_image_upload_size],
            ),
        ),
    ]
