from django.contrib import admin
from .models import ContactSubmission, OptionalPhoneCapture


@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "client", "created_at")
    list_filter = ("client",)
    search_fields = ("name", "email", "message")
    readonly_fields = ("name", "email", "phone", "message", "client", "created_at")


@admin.register(OptionalPhoneCapture)
class OptionalPhoneCaptureAdmin(admin.ModelAdmin):
    list_display = ("phone", "client", "created_at")
    list_filter = ("client",)
    search_fields = ("phone",)
    readonly_fields = ("phone", "client", "created_at")
