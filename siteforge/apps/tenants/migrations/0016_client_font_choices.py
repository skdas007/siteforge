from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0015_client_marketing_campaign_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="font_body",
            field=models.CharField(blank=True, default="inter", max_length=40),
        ),
        migrations.AddField(
            model_name="client",
            name="font_heading",
            field=models.CharField(blank=True, default="poppins", max_length=40),
        ),
    ]
