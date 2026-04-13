from decimal import Decimal

from django import forms

from apps.catalog.models import Category
from apps.core.validators import validate_favicon_upload, validate_image_upload_size

_IMAGE_HELP = "Maximum file size: 3 MB."

# Primary product image help_text; other sizes are in dashboard templates.
_REC_PRODUCT_MAIN = "Recommended: at least 800×800 px, or 1000×1000 / 1200×900 px for sharp grids and zoom (list cards ~220 px tall)."


class SiteSettingsForm(forms.Form):
    """Dashboard site settings; saves to Client."""
    hero_title = forms.CharField(max_length=200, required=False)
    hero_subtitle = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)
    theme = forms.ChoiceField(choices=[], required=True)
    contact_email = forms.EmailField(required=False)
    whatsapp_number = forms.CharField(
        max_length=20,
        required=False,
        label="WhatsApp number",
        help_text="With country code, no + or spaces (e.g. 919876543210). Used for 'Buy in WhatsApp' on product pages.",
    )
    map_embed_url = forms.URLField(
        required=False,
        label="Map embed URL",
        help_text="Paste an iframe embed URL from Google Maps or OpenStreetMap for the Contact section map.",
    )
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
        ]


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
