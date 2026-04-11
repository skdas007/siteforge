from django.contrib import admin
from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "client", "order")
    list_filter = ("client",)
    search_fields = ("name",)
    raw_id_fields = ("client",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "client", "category", "price", "compare_at_price", "is_active", "is_main", "order", "created_at")
    list_filter = ("is_active", "is_main", "client", "category")
    search_fields = ("name", "description", "seo_title", "seo_description")
    list_editable = ("order", "is_active", "is_main")
    raw_id_fields = ("client",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("client", "category", "name", "description", "price", "compare_at_price", "image", "order", "is_active", "is_main")}),
        ("SEO & social previews", {"fields": ("seo_title", "seo_description", "seo_image"), "classes": ("collapse",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
