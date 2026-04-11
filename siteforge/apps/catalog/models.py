"""Product and Category models: client-scoped."""
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.storage_cleanup import clear_missing_file_fields
from apps.core.validators import validate_image_upload_size


class Category(models.Model):
    """Category for products; each client has their own categories."""
    client = models.ForeignKey(
        "tenants.Client",
        on_delete=models.CASCADE,
        related_name="categories",
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    """Product belonging to a client. One per client can be main (shown on home page)."""
    client = models.ForeignKey(
        "tenants.Client",
        on_delete=models.CASCADE,
        related_name="products",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        blank=True,
        help_text="Sale price — what the customer pays.",
    )
    compare_at_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional original / MRP. If higher than sale price, the site shows a discount.",
    )
    image = models.ImageField(
        upload_to="catalog/products/",
        blank=True,
        null=True,
        validators=[validate_image_upload_size],
    )
    seo_title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional. Overrides the product name in search and link previews.",
    )
    seo_description = models.TextField(
        blank=True,
        help_text="Optional. Overrides the product description in search and social snippets.",
    )
    seo_image = models.ImageField(
        upload_to="catalog/seo/",
        blank=True,
        null=True,
        validators=[validate_image_upload_size],
        help_text="Optional. Image shown when this product link is shared. If empty, the primary product image is used. Max 3 MB.",
    )
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_main = models.BooleanField(
        default=False,
        help_text="Show this product on the home page. Only one product per site can be main.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.name} ({self.client.business_name})"

    @property
    def has_discount(self):
        mrp = self.compare_at_price
        if mrp is None:
            return False
        return mrp > self.price

    @property
    def discount_percent(self):
        """Rounded percent off (1–99), or None if negligible."""
        if not self.has_discount:
            return None
        mrp = self.compare_at_price
        if mrp is None or mrp <= 0:
            return None
        raw = ((mrp - self.price) / mrp) * Decimal("100")
        n = int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        if n < 1:
            return None
        return min(99, n)

    def clean(self):
        clear_missing_file_fields(self, "image", "seo_image")
        super().clean()
        if self.compare_at_price is not None and self.compare_at_price < self.price:
            raise ValidationError(
                {
                    "compare_at_price": "Original price (MRP) must be greater than or equal to the sale price.",
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.is_main:
            Product.objects.filter(client=self.client).exclude(pk=self.pk).update(is_main=False)
        super().save(*args, **kwargs)


class ProductImage(models.Model):
    """Extra image for a product (gallery). Product.image is the primary image."""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="extra_images",
    )
    image = models.ImageField(
        upload_to="catalog/product_images/",
        validators=[validate_image_upload_size],
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "pk"]

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
