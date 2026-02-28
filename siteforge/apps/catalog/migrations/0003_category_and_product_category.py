# Generated migration: Category and Product.category

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0002_productimage"),
    ]

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("slug", models.SlugField(blank=True, max_length=100)),
                ("order", models.PositiveIntegerField(default=0)),
                (
                    "client",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="categories",
                        to="tenants.client",
                    ),
                ),
            ],
            options={
                "ordering": ["order", "name"],
                "verbose_name_plural": "categories",
            },
        ),
        migrations.AddField(
            model_name="product",
            name="category",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="products",
                to="catalog.category",
            ),
        ),
    ]
