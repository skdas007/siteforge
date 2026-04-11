from django.conf import settings
from django.db import models

from apps.core.storage_cleanup import clear_missing_file_fields
from apps.core.validators import validate_image_upload_size, validate_video_upload_size


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
    banner_image = models.ImageField(
        upload_to="tenants/banners/",
        blank=True,
        null=True,
        validators=[validate_image_upload_size],
    )
    hero_title = models.CharField(max_length=300, blank=True)
    hero_subtitle = models.TextField(blank=True)
    hero_image = models.ImageField(
        upload_to="tenants/hero/",
        blank=True,
        null=True,
        help_text="Image shown on the right in the welcome/hero section below the carousel.",
        validators=[validate_image_upload_size],
    )
    logo = models.ImageField(
        upload_to="tenants/logos/",
        blank=True,
        null=True,
        validators=[validate_image_upload_size],
    )
    contact_email = models.EmailField(blank=True)
    whatsapp_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="WhatsApp number with country code (e.g. 919876543210). Used for 'Buy in WhatsApp' on product pages.",
    )
    seo_title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional. Overrides the home page title for Google and social previews. If empty, hero title and business name are used.",
    )
    seo_description = models.TextField(
        blank=True,
        help_text="Optional. Default description for your home page and product listing when you do not set a product-specific description. Aim for under ~160 characters.",
    )
    seo_image = models.ImageField(
        upload_to="tenants/seo/",
        blank=True,
        null=True,
        validators=[validate_image_upload_size],
        help_text="Optional. Default image when sharing your site (WhatsApp, Facebook, etc.). Recommended ~1200×630 px. Max 3 MB.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["business_name"]

    def __str__(self):
        return f"{self.business_name} ({self.domain})"

    def clean(self):
        super().clean()
        clear_missing_file_fields(
            self,
            "banner_image",
            "hero_image",
            "logo",
            "seo_image",
        )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

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
    image = models.ImageField(
        upload_to="tenants/carousel/",
        blank=True,
        null=True,
        validators=[validate_image_upload_size],
    )
    video = models.FileField(
        upload_to="tenants/carousel/",
        blank=True,
        null=True,
        validators=[validate_video_upload_size],
    )
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Slide {self.order} ({self.client.business_name})"

    def clean(self):
        super().clean()
        clear_missing_file_fields(self, "image", "video")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
