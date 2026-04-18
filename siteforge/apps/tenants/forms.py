from decimal import Decimal
from datetime import datetime, timedelta, timezone as dt_timezone

from django import forms
from django.utils import timezone
from django.utils.text import slugify

from apps.catalog.models import Category
from apps.tenants.models import LegalPage
from apps.core.validators import validate_favicon_upload, validate_image_upload_size

_IMAGE_HELP = "Maximum file size: 3 MB."
_FONT_CHOICES = [
    ("inter", "Inter (modern clean)"),
    ("poppins", "Poppins (geometric)"),
    ("dm-sans", "DM Sans (friendly)"),
    ("lato", "Lato (balanced)"),
    ("roboto", "Roboto (neutral)"),
    ("playfair", "Playfair Display (elegant serif)"),
    ("cormorant", "Cormorant Garamond (premium serif)"),
]

# Primary product image help_text; other sizes are in dashboard templates.
_REC_PRODUCT_MAIN = "Recommended: at least 800×800 px, or 1000×1000 / 1200×900 px for sharp grids and zoom (list cards ~220 px tall)."


class SiteSettingsForm(forms.Form):
    """Dashboard site settings; saves to Client."""
    hero_title = forms.CharField(max_length=200, required=False)
    hero_subtitle = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)
    theme = forms.ChoiceField(choices=[], required=True)
    font_body = forms.ChoiceField(choices=_FONT_CHOICES, required=False, initial="inter", label="Body font")
    font_heading = forms.ChoiceField(choices=_FONT_CHOICES, required=False, initial="poppins", label="Heading font")
    contact_email = forms.EmailField(required=False)
    footer_intro = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
        label="Footer intro text",
        help_text="Shown under your business name in footer.",
    )
    address_text = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
        label="Address",
        help_text="Shown in footer and contact block.",
    )
    whatsapp_number = forms.CharField(
        max_length=20,
        required=False,
        label="WhatsApp number",
        help_text="With country code, no + or spaces (e.g. 919876543210). Used for 'Buy in WhatsApp' on product pages.",
    )
    instagram_url = forms.URLField(required=False, label="Instagram URL")
    facebook_url = forms.URLField(required=False, label="Facebook URL")
    youtube_url = forms.URLField(required=False, label="YouTube URL")
    map_embed_url = forms.URLField(
        required=False,
        label="Map embed URL",
        help_text="Paste an iframe embed URL from Google Maps or OpenStreetMap for the Contact section map.",
    )
    announcement_enabled = forms.BooleanField(required=False, label="Enable announcement bar")
    announcement_text = forms.CharField(max_length=240, required=False, label="Announcement text")
    announcement_cta_label = forms.CharField(max_length=40, required=False, label="Announcement button label")
    announcement_cta_url = forms.URLField(required=False, label="Announcement button URL")
    announcement_bg_color = forms.CharField(max_length=7, required=False, label="Announcement background color")
    announcement_text_color = forms.CharField(max_length=7, required=False, label="Announcement text color")
    popup_enabled = forms.BooleanField(required=False, label="Enable popup campaign")
    popup_title = forms.CharField(max_length=160, required=False, label="Popup title")
    popup_message = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False, label="Popup message")
    popup_image = forms.ImageField(
        required=False,
        validators=[validate_image_upload_size],
        label="Popup image",
        help_text=_IMAGE_HELP,
    )
    popup_cta_label = forms.CharField(max_length=40, required=False, label="Popup button label")
    popup_cta_url = forms.URLField(required=False, label="Popup button URL")
    popup_show_rule = forms.ChoiceField(
        required=False,
        choices=[
            ("always", "Show every page load"),
            ("session", "Once per browser session"),
            ("day", "Once per day"),
        ],
        initial="session",
        label="Popup show rule",
    )
    popup_start_at = forms.CharField(required=False, label="Popup start")
    popup_end_at = forms.CharField(required=False, label="Popup end")
    popup_timezone_offset = forms.IntegerField(required=False)
    banner_image = forms.ImageField(
        required=False,
        validators=[validate_image_upload_size],
        help_text=_IMAGE_HELP,
    )
    hero_image = forms.ImageField(
        required=False,
        label="Welcome image",
        validators=[validate_image_upload_size],
        help_text=_IMAGE_HELP,
    )
    logo = forms.ImageField(
        required=False,
        validators=[validate_image_upload_size],
        help_text=_IMAGE_HELP,
    )
    favicon = forms.FileField(
        required=False,
        validators=[validate_favicon_upload],
        label="Favicon (browser tab icon)",
        help_text="Use .ico, PNG, or SVG. Max 512 KB. Typical size 32×32 or 48×48 px.",
    )
    seo_title = forms.CharField(
        max_length=200,
        required=False,
        label="SEO title (home)",
        help_text="Optional. Shown in Google and when sharing your home page. If empty, hero title and business name are used.",
    )
    seo_description = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
        label="SEO description (default)",
        help_text="Optional. Default snippet for your home and products listing. Product-specific SEO overrides this on product pages.",
    )
    seo_keywords = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
        label="SEO keywords",
        help_text="Optional comma-separated keywords.",
    )
    seo_author = forms.CharField(max_length=200, required=False, label="SEO author / brand")
    seo_robots = forms.CharField(max_length=40, required=False, label="Robots", initial="index, follow")
    seo_language = forms.CharField(max_length=40, required=False, label="Language", initial="English")
    seo_revisit_after = forms.CharField(max_length=40, required=False, label="Revisit after", initial="7 days")
    seo_geo_region = forms.CharField(max_length=24, required=False, label="Geo region")
    seo_geo_placename = forms.CharField(max_length=120, required=False, label="Geo place name")
    seo_geo_position = forms.CharField(max_length=50, required=False, label="Geo position")
    seo_icbm = forms.CharField(max_length=50, required=False, label="ICBM")
    seo_founder = forms.CharField(max_length=120, required=False, label="Founder")
    seo_address_locality = forms.CharField(max_length=120, required=False, label="Address locality")
    seo_postal_code = forms.CharField(max_length=20, required=False, label="Postal code")
    seo_address_region = forms.CharField(max_length=120, required=False, label="Address region")
    seo_address_country = forms.CharField(max_length=10, required=False, label="Address country", initial="IN")
    seo_image = forms.ImageField(
        required=False,
        validators=[validate_image_upload_size],
        label="SEO / share image (default)",
        help_text=_IMAGE_HELP,
    )

    def __init__(self, theme_choices=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["theme"].choices = theme_choices or [
            ("default", "Default"),
            ("minimal", "Minimal"),
            ("clarity", "Clarity (agency style + animations)"),
            ("aurora", "Aurora (colorful gradient)"),
            ("midnight", "Midnight (dark mode)"),
            ("blackred", "Black Red (bold contrast)"),
            ("emeraldgold", "Emerald Gold (premium)"),
            ("goldforest", "Golden Forest (Gold + Forest)"),
        ]

    def clean(self):
        cleaned = super().clean()
        offset_raw = cleaned.get("popup_timezone_offset")
        try:
            offset_minutes = int(offset_raw)
        except (TypeError, ValueError):
            offset_minutes = 0

        def parse_local_dt(raw):
            raw = (raw or "").strip()
            if not raw:
                return None
            try:
                local_naive = datetime.strptime(raw, "%Y-%m-%dT%H:%M")
            except ValueError:
                raise forms.ValidationError("Enter date/time in valid format.")
            # Browser gives local wall time. Convert to UTC using browser offset.
            utc_naive = local_naive + timedelta(minutes=offset_minutes)
            return timezone.make_aware(utc_naive, dt_timezone.utc)

        try:
            start = parse_local_dt(cleaned.get("popup_start_at"))
        except forms.ValidationError:
            self.add_error("popup_start_at", "Enter a valid popup start date/time.")
            start = None
        try:
            end = parse_local_dt(cleaned.get("popup_end_at"))
        except forms.ValidationError:
            self.add_error("popup_end_at", "Enter a valid popup end date/time.")
            end = None

        cleaned["popup_start_at"] = start
        cleaned["popup_end_at"] = end
        if start and end and end <= start:
            self.add_error("popup_end_at", "Popup end must be after popup start.")
        return cleaned


class CategoryForm(forms.ModelForm):
    """Dashboard: create / edit category including home Spotlight tile."""

    class Meta:
        model = Category
        fields = [
            "name",
            "show_in_spotlight",
            "spotlight_order",
            "spotlight_image",
            "spotlight_video",
            "spotlight_headline",
            "spotlight_upto_label",
            "spotlight_discount_text",
            "spotlight_subtitle",
            "spotlight_tag_style",
            "spotlight_tag_text",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Silk collection",
                    "maxlength": 100,
                    "id": "id_name",
                }
            ),
            "show_in_spotlight": forms.CheckboxInput(attrs={"class": "form-check-input", "id": "id_show_in_spotlight"}),
            "spotlight_order": forms.NumberInput(attrs={"class": "form-control", "min": 0, "id": "id_spotlight_order"}),
            "spotlight_image": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "spotlight_video": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "video/mp4,.mp4"}),
            "spotlight_headline": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. Festival sale", "maxlength": 120}
            ),
            "spotlight_upto_label": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Leave blank for “Upto”", "maxlength": 30}
            ),
            "spotlight_discount_text": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. 15% OFF", "maxlength": 40}
            ),
            "spotlight_subtitle": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Blank uses category name", "maxlength": 120}
            ),
            "spotlight_tag_style": forms.Select(attrs={"class": "form-control"}),
            "spotlight_tag_text": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. From ₹1,299 or SKU-102", "maxlength": 80}
            ),
        }

    def __init__(self, *args, client=None, editing_pk=None, **kwargs):
        self._client = client
        self._editing_pk = editing_pk
        super().__init__(*args, **kwargs)
        for fname in ("spotlight_image", "spotlight_video"):
            if fname in self.fields:
                self.fields[fname].required = False

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Category name is required.")
        if not self._client:
            return name
        qs = Category.objects.filter(client=self._client, name__iexact=name)
        if self._editing_pk:
            qs = qs.exclude(pk=self._editing_pk)
        if qs.exists():
            raise forms.ValidationError("A category with that name already exists.")
        return name[:100]


class ProductForm(forms.Form):
    """Dashboard product add/edit; saves to catalog.Product."""
    name = forms.CharField(max_length=200, required=True)
    description = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)
    price = forms.DecimalField(
        required=False,
        label="Sale price",
        help_text="What the customer pays (shown prominently).",
    )
    compare_at_price = forms.DecimalField(
        required=False,
        label="Original price (MRP)",
        help_text="Optional. If higher than sale price, the site shows strikethrough MRP and discount like Flipkart/Amazon.",
    )
    category = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="— No category —",
        label="Category",
        help_text="Optional. Use categories to filter products on your site.",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    image = forms.ImageField(
        required=False,
        validators=[validate_image_upload_size],
        help_text=f"{_REC_PRODUCT_MAIN} {_IMAGE_HELP}",
    )
    is_active = forms.BooleanField(required=False, initial=True)
    is_main = forms.BooleanField(
        required=False,
        initial=False,
        label="Main product (show on home page)",
        help_text="Only one product can be main. It will appear on your home page.",
    )
    seo_title = forms.CharField(
        max_length=200,
        required=False,
        label="SEO title",
        help_text="Optional. Overrides the product name in search results and social previews.",
    )
    seo_description = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
        label="SEO description",
        help_text="Optional. Overrides the product description in snippets. If empty, the main description is used.",
    )
    seo_keywords = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
        label="SEO keywords",
        help_text="Optional comma-separated keywords for this product page.",
    )
    seo_image = forms.ImageField(
        required=False,
        validators=[validate_image_upload_size],
        label="SEO / share image",
        help_text=_IMAGE_HELP,
    )

    def __init__(self, category_queryset=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if category_queryset is not None:
            self.fields["category"].queryset = category_queryset

    def clean(self):
        cleaned = super().clean()
        sale = cleaned.get("price")
        mrp = cleaned.get("compare_at_price")
        if sale is None:
            sale = Decimal("0")
        if mrp is not None and mrp < sale:
            self.add_error(
                "compare_at_price",
                "Original price (MRP) must be greater than or equal to the sale price.",
            )
        return cleaned


class LegalPageForm(forms.ModelForm):
    class Meta:
        model = LegalPage
        fields = ["title", "slug", "page_type", "content", "show_in_footer", "is_active"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "maxlength": 160}),
            "slug": forms.TextInput(
                attrs={"class": "form-control", "maxlength": 180, "placeholder": "Add an unique slug for the page"}
            ),
            "page_type": forms.Select(attrs={"class": "form-select"}),
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 8}),
            "show_in_footer": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, client=None, editing_pk=None, **kwargs):
        self._client = client
        self._editing_pk = editing_pk
        super().__init__(*args, **kwargs)

    def clean_title(self):
        title = (self.cleaned_data.get("title") or "").strip()
        if not title:
            raise forms.ValidationError("Title is required.")
        return title[:160]

    def clean_slug(self):
        raw_slug = (self.cleaned_data.get("slug") or "").strip()
        title = (self.cleaned_data.get("title") or "").strip()
        slug = slugify(raw_slug or title)[:180]
        if not slug:
            raise forms.ValidationError("Slug is required.")
        if not self._client:
            return slug
        qs = LegalPage.objects.filter(client=self._client, slug=slug)
        if self._editing_pk:
            qs = qs.exclude(pk=self._editing_pk)
        if qs.exists():
            raise forms.ValidationError("A page with this slug already exists.")
        return slug
