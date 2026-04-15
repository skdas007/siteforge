from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0010_productsizevariant_stock_qty"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="seo_keywords",
            field=models.TextField(blank=True, help_text="Optional comma-separated keywords for this product page."),
        ),
    ]
