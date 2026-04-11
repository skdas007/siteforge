# Generated manually for product SEO fields

import apps.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0005_product_compare_at_price"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="seo_title",
            field=models.CharField(
                blank=True,
                help_text="Optional. Overrides the product name in search and link previews.",
                max_length=200,
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="seo_description",
            field=models.TextField(
                blank=True,
                help_text="Optional. Overrides the product description in search and social snippets.",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="seo_image",
            field=models.ImageField(
                blank=True,
                help_text="Optional. Image shown when this product link is shared. If empty, the primary product image is used. Max 3 MB.",
                null=True,
                upload_to="catalog/seo/",
                validators=[apps.core.validators.validate_image_upload_size],
            ),
        ),
    ]
