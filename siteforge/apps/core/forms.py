from django import forms


class ContactForm(forms.Form):
    """Public contact form; saves to ContactSubmission."""
    name = forms.CharField(
        max_length=200,
        required=True,
        min_length=2,
        strip=True,
        error_messages={"required": "Please enter your name.", "min_length": "Name must be at least 2 characters."},
    )
    email = forms.EmailField(
        required=True,
        error_messages={"required": "Please enter your email.", "invalid": "Please enter a valid email address."},
    )
    phone = forms.CharField(max_length=50, required=False, strip=True)
    message = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        required=True,
        min_length=10,
        strip=True,
        error_messages={"required": "Please enter your message.", "min_length": "Message must be at least 10 characters."},
    )

    def clean_name(self):
        data = (self.cleaned_data.get("name") or "").strip()
        if len(data) < 2:
            raise forms.ValidationError("Name must be at least 2 characters.")
        return data[:200]

    def clean_message(self):
        data = (self.cleaned_data.get("message") or "").strip()
        if len(data) < 10:
            raise forms.ValidationError("Message must be at least 10 characters.")
        return data
