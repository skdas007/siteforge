from django.db import models


class Theme(models.Model):
    """CSS-only theme; styles in static/themes/<slug>/."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=50, unique=True)
    preview_image = models.ImageField(upload_to="themes/previews/", blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
