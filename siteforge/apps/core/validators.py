"""Shared upload limits for the project."""
import os

from django.core.exceptions import ValidationError

# Maximum upload sizes (bytes)
MAX_IMAGE_UPLOAD_BYTES = 3 * 1024 * 1024  # 3 MB — all images project-wide
MAX_VIDEO_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB — carousel MP4 only
# Additional gallery images per product (ProductImage), dashboard multi-upload.
MAX_PRODUCT_GALLERY_IMAGES = 3
MAX_FAVICON_BYTES = 512 * 1024  # 512 KB — browser tab icons
_FAVICON_EXTENSIONS = frozenset({"ico", "png", "svg", "webp", "gif"})


def _file_field_size(value):
    """Return file size in bytes, or None if missing / not on storage (e.g. stale S3 key)."""
    if value in (None, False, ""):
        return None
    try:
        return getattr(value, "size", None)
    except (FileNotFoundError, OSError):
        return None


def validate_image_upload_size(value):
    """Reject image uploads over MAX_IMAGE_UPLOAD_BYTES."""
    size = _file_field_size(value)
    if size is not None and size > MAX_IMAGE_UPLOAD_BYTES:
        raise ValidationError(
            "Image file size must be at most 3 MB.",
            code="image_too_large",
        )


def validate_video_upload_size(value):
    """Reject video uploads over MAX_VIDEO_UPLOAD_BYTES (carousel)."""
    size = _file_field_size(value)
    if size is not None and size > MAX_VIDEO_UPLOAD_BYTES:
        raise ValidationError(
            "Video file size must be at most 15 MB.",
            code="video_too_large",
        )


def validate_favicon_upload(value):
    """Reject non-icon types or oversized favicon files (.ico, .png, .svg, .webp, .gif)."""
    if value in (None, False, ""):
        return
    name = getattr(value, "name", "") or ""
    ext = os.path.splitext(name)[1].lower().lstrip(".")
    if ext not in _FAVICON_EXTENSIONS:
        raise ValidationError(
            "Favicon must be a .ico, .png, .svg, .webp, or .gif file.",
            code="favicon_extension",
        )
    size = _file_field_size(value)
    if size is not None and size > MAX_FAVICON_BYTES:
        raise ValidationError(
            "Favicon file size must be at most 512 KB.",
            code="favicon_too_large",
        )
