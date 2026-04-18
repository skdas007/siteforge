from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0012_client_footer_contact_social_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="footer_intro",
            field=models.TextField(blank=True, help_text="Short text shown under business name in footer."),
        ),
    ]
