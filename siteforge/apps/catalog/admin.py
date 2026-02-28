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
    list_display = ("name", "client", "category", "price", "is_active", "is_main", "order", "created_at")
    list_filter = ("is_active", "is_main", "client", "category")
    search_fields = ("name", "description")
    list_editable = ("order", "is_active", "is_main")
    raw_id_fields = ("client",)
    readonly_fields = ("created_at", "updated_at")
