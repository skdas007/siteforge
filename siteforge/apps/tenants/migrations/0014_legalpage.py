from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0013_client_footer_intro"),
    ]

    operations = [
        migrations.CreateModel(
            name="LegalPage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=160)),
                ("slug", models.SlugField(max_length=180)),
                (
                    "page_type",
                    models.CharField(
                        choices=[
                            ("terms", "Terms & Conditions"),
                            ("privacy", "Privacy Policy"),
                            ("custom", "Custom page"),
                        ],
                        default="custom",
                        max_length=20,
                    ),
                ),
                ("content", models.TextField(blank=True)),
                ("show_in_footer", models.BooleanField(default=True)),
                ("is_active", models.BooleanField(default=True)),
                ("order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "client",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="legal_pages", to="tenants.client"),
                ),
            ],
            options={
                "ordering": ["order", "title", "pk"],
            },
        ),
        migrations.AddConstraint(
            model_name="legalpage",
            constraint=models.UniqueConstraint(fields=("client", "slug"), name="uniq_legalpage_client_slug"),
        ),
    ]
