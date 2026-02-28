from django import forms


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
    banner_image = forms.ImageField(required=False)
    hero_image = forms.ImageField(required=False, label="Welcome image")
    logo = forms.ImageField(required=False)

    def __init__(self, theme_choices=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["theme"].choices = theme_choices or [
            ("default", "Default"),
            ("minimal", "Minimal"),
            ("clarity", "Clarity (agency style + animations)"),
        ]


class ProductForm(forms.Form):
    """Dashboard product add/edit; saves to catalog.Product."""
    name = forms.CharField(max_length=200, required=True)
    description = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)
    price = forms.DecimalField(required=False)
    category = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="— No category —",
        label="Category",
        help_text="Optional. Use categories to filter products on your site.",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    image = forms.ImageField(required=False)
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
