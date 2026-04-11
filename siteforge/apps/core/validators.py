"""Shared upload limits for the project."""
from django.core.exceptions import ValidationError

# Maximum upload sizes (bytes)
MAX_IMAGE_UPLOAD_BYTES = 3 * 1024 * 1024  # 3 MB — all images project-wide
MAX_VIDEO_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB — carousel MP4 only


def validate_image_upload_size(value):
    """Reject image uploads over MAX_IMAGE_UPLOAD_BYTES."""
    if value in (None, False, ""):
        return
    size = getattr(value, "size", None)
    if size is not None and size > MAX_IMAGE_UPLOAD_BYTES:
        raise ValidationError(
            "Image file size must be at most 3 MB.",
            code="image_too_large",
        )


def validate_video_upload_size(value):
    """Reject video uploads over MAX_VIDEO_UPLOAD_BYTES (carousel)."""
    if value in (None, False, ""):
        return
    size = getattr(value, "size", None)
    if size is not None and size > MAX_VIDEO_UPLOAD_BYTES:
        raise ValidationError(
            "Video file size must be at most 15 MB.",
            code="video_too_large",
        )
