from django.conf import settings
from django.db import models


class Client(models.Model):
    """Tenant: one per site; resolved by domain in middleware."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="client",
        null=True,
        blank=True,
        help_text="Login for dashboard; optional for admin-created clients.",
    )
    business_name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=80, unique=True)
    domain = models.CharField(max_length=255, unique=True, db_index=True)
    theme = models.ForeignKey(
        "themes.Theme",
        on_delete=models.PROTECT,
        related_name="clients",
        null=True,
        blank=True,
    )
    banner_image = models.ImageField(upload_to="tenants/banners/", blank=True, null=True)
    hero_title = models.CharField(max_length=300, blank=True)
    hero_subtitle = models.TextField(blank=True)
    hero_image = models.ImageField(
        upload_to="tenants/hero/",
        blank=True,
        null=True,
        help_text="Image shown on the right in the welcome/hero section below the carousel.",
    )
    logo = models.ImageField(upload_to="tenants/logos/", blank=True, null=True)
    contact_email = models.EmailField(blank=True)
    whatsapp_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="WhatsApp number with country code (e.g. 919876543210). Used for 'Buy in WhatsApp' on product pages.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["business_name"]

    def __str__(self):
        return f"{self.business_name} ({self.domain})"

    @property
    def theme_slug(self):
        if self.theme_id:
            return self.theme.slug
        return "default"


class CarouselSlide(models.Model):
    """One image or video + caption in a client's homepage carousel."""
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="carousel_slides",
    )
    image = models.ImageField(upload_to="tenants/carousel/", blank=True, null=True)
    video = models.FileField(upload_to="tenants/carousel/", blank=True, null=True)
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Slide {self.order} ({self.client.business_name})"
