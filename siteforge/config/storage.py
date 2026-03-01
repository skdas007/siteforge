"""
Custom S3 storage so media URLs include the location prefix (e.g. media/).
Fixes the case where generated URLs are missing 'media/' and point to the wrong path.
"""
from storages.backends.s3 import S3Storage


class S3MediaStorage(S3Storage):
    """S3 storage that ensures location=media so URLs are .../media/catalog/... not .../catalog/..."""

    def __init__(self, **kwargs):
        if not (kwargs.get("location") or "").strip():
            kwargs["location"] = "media"
        super().__init__(**kwargs)
