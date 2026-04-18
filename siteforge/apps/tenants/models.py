from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.core.image_compression import compress_model_image_fields
from apps.core.storage_cleanup import clear_missing_file_fields
from apps.core.validators import (
    validate_favicon_upload,
    validate_image_upload_size,
    validate_video_upload_size,
)

FONT_META = {
    "inter": {"css": '"Inter", system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif', "google": "Inter:wght@400;500;600;700"},
    "poppins": {"css": '"Poppins", system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif', "google": "Poppins:wght@400;500;600;700"},
    "dm-sans": {"css": '"DM Sans", system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif', "google": "DM+Sans:wght@400;500;700"},
    "lato": {"css": '"Lato", "Helvetica Neue", Arial, sans-serif', "google": "Lato:wght@400;700"},
    "roboto": {"css": '"Roboto", "Helvetica Neue", Arial, sans-serif', "google": "Roboto:wght@400;500;700"},
    "playfair": {"css": '"Playfair Display", Georgia, "Times New Roman", serif', "google": "Playfair+Display:wght@500;600;700"},
    "cormorant": {"css": '"Cormorant Garamond", Georgia, "Times New Roman", serif', "google": "Cormorant+Garamond:wght@500;600;700"},
}


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
    font_body = models.CharField(max_length=40, blank=True, default="inter")
    font_heading = models.CharField(max_length=40, blank=True, default="poppins")
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
    favicon = models.FileField(
        upload_to="tenants/favicons/",
        blank=True,
        null=True,
        validators=[validate_favicon_upload],
        help_text="Browser tab icon (.ico, PNG, or SVG). Max 512 KB.",
    )
    contact_email = models.EmailField(blank=True)
    footer_intro = models.TextField(
        blank=True,
        help_text="Short text shown under business name in footer.",
    )
    address_text = models.TextField(
        blank=True,
        help_text="Business address shown in footer/contact sections.",
    )
    whatsapp_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="WhatsApp number with country code (e.g. 919876543210). Used for 'Buy in WhatsApp' on product pages.",
    )
    instagram_url = models.URLField(max_length=500, blank=True)
    facebook_url = models.URLField(max_length=500, blank=True)
    youtube_url = models.URLField(max_length=500, blank=True)
    map_embed_url = models.URLField(
        max_length=1200,
        blank=True,
        help_text="Optional map embed URL for Contact section iframe (Google Maps / OpenStreetMap embed link).",
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
    seo_keywords = models.TextField(
        blank=True,
        help_text="Optional comma-separated keywords for search engines.",
    )
    seo_author = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional author/brand meta tag.",
    )
    seo_robots = models.CharField(
        max_length=40,
        blank=True,
        default="index, follow",
        help_text="Robots directive, e.g. index, follow",
    )
    seo_language = models.CharField(max_length=40, blank=True, default="English")
    seo_revisit_after = models.CharField(max_length=40, blank=True, default="7 days")
    seo_geo_region = models.CharField(max_length=24, blank=True, help_text="Example: IN-OD")
    seo_geo_placename = models.CharField(max_length=120, blank=True, help_text="Example: Bhuban, Odisha")
    seo_geo_position = models.CharField(max_length=50, blank=True, help_text="Example: 20.881;85.833")
    seo_icbm = models.CharField(max_length=50, blank=True, help_text="Example: 20.881,85.833")
    seo_founder = models.CharField(max_length=120, blank=True, help_text="Founder name for Organization schema.")
    seo_address_locality = models.CharField(max_length=120, blank=True)
    seo_postal_code = models.CharField(max_length=20, blank=True)
    seo_address_region = models.CharField(max_length=120, blank=True)
    seo_address_country = models.CharField(max_length=10, blank=True, default="IN")
    seo_image = models.ImageField(
        upload_to="tenants/seo/",
        blank=True,
        null=True,
        validators=[validate_image_upload_size],
        help_text="Optional. Default image when sharing your site (WhatsApp, Facebook, etc.). Recommended ~1200×630 px. Max 3 MB.",
    )
    announcement_enabled = models.BooleanField(default=False)
    announcement_text = models.CharField(max_length=240, blank=True)
    announcement_cta_label = models.CharField(max_length=40, blank=True)
    announcement_cta_url = models.URLField(max_length=800, blank=True)
    announcement_bg_color = models.CharField(max_length=7, blank=True, default="#0d6efd")
    announcement_text_color = models.CharField(max_length=7, blank=True, default="#ffffff")
    popup_enabled = models.BooleanField(default=False)
    popup_title = models.CharField(max_length=160, blank=True)
    popup_message = models.TextField(blank=True)
    popup_image = models.ImageField(
        upload_to="tenants/popup/",
        blank=True,
        null=True,
        validators=[validate_image_upload_size],
        help_text="Optional campaign popup image. Max 3 MB.",
    )
    popup_cta_label = models.CharField(max_length=40, blank=True)
    popup_cta_url = models.URLField(max_length=800, blank=True)
    popup_show_rule = models.CharField(
        max_length=20,
        blank=True,
        default="session",
        choices=[
            ("always", "Show every page load"),
            ("session", "Once per browser session"),
            ("day", "Once per day"),
        ],
    )
    popup_start_at = models.DateTimeField(blank=True, null=True)
    popup_end_at = models.DateTimeField(blank=True, null=True)
    popup_impressions = models.PositiveIntegerField(default=0)
    popup_clicks = models.PositiveIntegerField(default=0)
    popup_closes = models.PositiveIntegerField(default=0)
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
            "favicon",
            "seo_image",
            "popup_image",
        )

    def save(self, *args, **kwargs):
        compress_model_image_fields(
            self,
            [
                ("banner_image", settings.IMAGE_UPLOAD_BANNER_MAX_SIDE),
                ("hero_image", settings.IMAGE_UPLOAD_BANNER_MAX_SIDE),
                ("logo", settings.IMAGE_UPLOAD_LOGO_MAX_SIDE),
                ("seo_image", settings.IMAGE_UPLOAD_SEO_MAX_SIDE),
                ("popup_image", settings.IMAGE_UPLOAD_BANNER_MAX_SIDE),
            ],
        )
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def theme_slug(self):
        if self.theme_id:
            return self.theme.slug
        return "default"

    def _font_key(self, raw, default):
        key = (raw or default or "").strip().lower()
        return key if key in FONT_META else default

    @property
    def font_body_key(self):
        return self._font_key(self.font_body, "inter")

    @property
    def font_heading_key(self):
        return self._font_key(self.font_heading, "poppins")

    @property
    def font_body_css(self):
        return FONT_META[self.font_body_key]["css"]

    @property
    def font_heading_css(self):
        return FONT_META[self.font_heading_key]["css"]

    @property
    def font_google_families_query(self):
        families = {
            FONT_META[self.font_body_key]["google"],
            FONT_META[self.font_heading_key]["google"],
        }
        return "|".join(sorted(families))


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
        compress_model_image_fields(self, [("image", settings.IMAGE_UPLOAD_BANNER_MAX_SIDE)])
        self.full_clean()
        super().save(*args, **kwargs)


class LegalPage(models.Model):
    """Client-managed legal/static content pages (terms, privacy, custom)."""

    PAGE_TYPE_TERMS = "terms"
    PAGE_TYPE_PRIVACY = "privacy"
    PAGE_TYPE_CUSTOM = "custom"
    PAGE_TYPE_CHOICES = [
        (PAGE_TYPE_TERMS, "Terms & Conditions"),
        (PAGE_TYPE_PRIVACY, "Privacy Policy"),
        (PAGE_TYPE_CUSTOM, "Custom page"),
    ]

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="legal_pages",
    )
    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180)
    page_type = models.CharField(max_length=20, choices=PAGE_TYPE_CHOICES, default=PAGE_TYPE_CUSTOM)
    content = models.TextField(blank=True)
    show_in_footer = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "title", "pk"]
        constraints = [
            models.UniqueConstraint(fields=["client", "slug"], name="uniq_legalpage_client_slug"),
        ]

    def __str__(self):
        return f"{self.title} ({self.client.business_name})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:180]
        self.full_clean()
        super().save(*args, **kwargs)
