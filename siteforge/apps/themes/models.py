from django.db import models

from apps.core.storage_cleanup import clear_missing_file_fields
from apps.core.validators import validate_image_upload_size


class Theme(models.Model):
    """CSS-only theme; styles in static/themes/<slug>/."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=50, unique=True)
    preview_image = models.ImageField(
        upload_to="themes/previews/",
        blank=True,
        null=True,
        validators=[validate_image_upload_size],
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        clear_missing_file_fields(self, "preview_image")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
