# Generated migration: carousel supports image or MP4 video

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0003_add_hero_image"),
    ]

    operations = [
        migrations.AlterField(
            model_name="carouselslide",
            name="image",
            field=models.ImageField(blank=True, null=True, upload_to="tenants/carousel/"),
        ),
        migrations.AddField(
            model_name="carouselslide",
            name="video",
            field=models.FileField(blank=True, null=True, upload_to="tenants/carousel/"),
        ),
    ]
