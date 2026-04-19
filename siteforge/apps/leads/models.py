from django.db import models


class OptionalPhoneCapture(models.Model):
    """Optional phone number from the public 'stay in touch' modal (per-tenant)."""

    client = models.ForeignKey(
        "tenants.Client",
        on_delete=models.CASCADE,
        related_name="optional_phone_captures",
    )
    phone = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "optional phone capture"
        verbose_name_plural = "optional phone captures"

    def __str__(self):
        return f"{self.phone} @ {self.client_id} ({self.created_at})"


class ContactSubmission(models.Model):
    """Contact form submission; scoped to client when available."""
    client = models.ForeignKey(
        "tenants.Client",
        on_delete=models.CASCADE,
        related_name="contact_submissions",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.email})"
