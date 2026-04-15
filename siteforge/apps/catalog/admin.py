from django.contrib import admin
from .models import Category, Product, ProductSizeVariant


class ProductSizeVariantInline(admin.TabularInline):
    model = ProductSizeVariant
    extra = 1
    fields = ("order", "size_label", "measurement_cm", "measurement_inch", "price", "compare_at_price", "stock_qty")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "client", "order", "show_in_spotlight", "spotlight_order")
    list_filter = ("client", "show_in_spotlight")
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
    inlines = (ProductSizeVariantInline,)
    fieldsets = (
        (None, {"fields": ("client", "category", "name", "description", "price", "compare_at_price", "image", "order", "is_active", "is_main")}),
        ("SEO & social previews", {"fields": ("seo_title", "seo_description", "seo_keywords", "seo_image"), "classes": ("collapse",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
