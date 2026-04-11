"""Delete product/product image files from storage when deleted."""
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Product, ProductImage


@receiver(post_delete, sender=Product)
def delete_product_image(sender, instance, **kwargs):
    if instance.image:
        try:
            instance.image.delete(save=False)
        except Exception:
            pass
    if getattr(instance, "seo_image", None):
        try:
            instance.seo_image.delete(save=False)
        except Exception:
            pass


@receiver(post_delete, sender=ProductImage)
def delete_product_image_file(sender, instance, **kwargs):
    if instance.image:
        try:
            instance.image.delete(save=False)
        except Exception:
            pass
