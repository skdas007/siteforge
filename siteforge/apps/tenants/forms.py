from decimal import Decimal

from django import forms

from apps.core.validators import validate_image_upload_size

_IMAGE_HELP = "Maximum file size: 3 MB."


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

    def __init__(self, theme_choices=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["theme"].choices = theme_choices or [
            ("default", "Default"),
            ("minimal", "Minimal"),
            ("clarity", "Clarity (agency style + animations)"),
        ]


class CategoryForm(forms.Form):
    """Dashboard: add product category (client-scoped in view)."""
    name = forms.CharField(
        label="Name",
        max_length=100,
        required=True,
        strip=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g. Electronics",
                "maxlength": 100,
                "id": "id_name",
            }
        ),
        error_messages={"required": "Category name is required."},
    )


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
        help_text=_IMAGE_HELP,
    )
    is_active = forms.BooleanField(required=False, initial=True)
    is_main = forms.BooleanField(
        required=False,
        initial=False,
        label="Main product (show on home page)",
        help_text="Only one product can be main. It will appear on your home page.",
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
