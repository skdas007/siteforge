from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0009_productsizevariant_compare_at_price"),
    ]

    operations = [
        migrations.AddField(
            model_name="productsizevariant",
            name="stock_qty",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
