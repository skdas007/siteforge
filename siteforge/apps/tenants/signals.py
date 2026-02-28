"""Delete files from storage (e.g. S3) when model instances are removed."""
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import CarouselSlide


def _delete_file_from_storage(file_field):
    """Delete the file from storage if it exists. Safe if storage is S3 or local."""
    if not file_field:
        return
    try:
        file_field.delete(save=False)
    except Exception:
        pass  # Avoid breaking delete if storage fails (e.g. file already gone)


@receiver(post_delete, sender=CarouselSlide)
def delete_carousel_slide_media(sender, instance, **kwargs):
    """When a CarouselSlide is deleted, remove its image and video from S3/storage."""
    _delete_file_from_storage(instance.image)
    _delete_file_from_storage(instance.video)
