from django.contrib import admin
from .models import CarouselSlide, Client


class CarouselSlideInline(admin.TabularInline):
    model = CarouselSlide
    extra = 0
    ordering = ("order",)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("business_name", "domain", "theme", "is_active", "created_at")
    list_filter = ("is_active", "theme")
    search_fields = ("business_name", "domain", "contact_email", "seo_title")
    prepopulated_fields = {"slug": ("business_name",)}
    raw_id_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("user", "business_name", "slug", "domain", "theme", "is_active")}),
        ("Content", {"fields": ("hero_title", "hero_subtitle", "banner_image", "hero_image", "logo", "contact_email", "whatsapp_number")}),
        ("SEO & social previews", {"fields": ("seo_title", "seo_description", "seo_image"), "classes": ("collapse",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
    inlines = [CarouselSlideInline]
