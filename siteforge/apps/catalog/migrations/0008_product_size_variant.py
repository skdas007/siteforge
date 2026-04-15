from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0007_category_spotlight_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductSizeVariant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("size_label", models.CharField(help_text="Examples: XS, S, M, L, XL", max_length=40)),
                ("measurement_cm", models.CharField(blank=True, help_text="Optional, e.g. Chest 96-100", max_length=60)),
                ("measurement_inch", models.CharField(blank=True, help_text="Optional, e.g. Chest 38-40", max_length=60)),
                ("price", models.DecimalField(decimal_places=2, max_digits=12)),
                ("order", models.PositiveIntegerField(default=0)),
                (
                    "product",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="size_variants", to="catalog.product"),
                ),
            ],
            options={
                "ordering": ["order", "pk"],
                "unique_together": {("product", "size_label")},
            },
        ),
    ]
