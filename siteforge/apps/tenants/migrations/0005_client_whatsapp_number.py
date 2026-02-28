# Generated migration: WhatsApp number for Buy in WhatsApp

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0004_carousel_video"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="whatsapp_number",
            field=models.CharField(
                blank=True,
                help_text="WhatsApp number with country code (e.g. 919876543210). Used for 'Buy in WhatsApp' on product pages.",
                max_length=20,
            ),
        ),
    ]
