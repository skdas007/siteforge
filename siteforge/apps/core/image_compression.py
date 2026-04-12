"""
Resize and re-encode raster uploads as WebP (optional AVIF) to save bandwidth.

Skips: new uploads that are not decodable by Pillow (e.g. SVG), animated GIFs,
and processing when IMAGE_AUTO_COMPRESS is False (unless overridden).
"""

from __future__ import annotations

import io
import uuid

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError


def compress_model_image_fields(instance, field_max_side: list[tuple[str, int]]) -> None:
    """Replace uncommitted ImageField files on instance with compressed versions."""
    for field_name, max_side in field_max_side:
        ff = getattr(instance, field_name, None)
        if not ff:
            continue
        if getattr(ff, "_committed", True):
            continue
        new_file = compress_image_upload(ff, max_side=max_side)
        if new_file is not None:
            setattr(instance, field_name, new_file)


def compress_image_upload(file_obj, *, max_side: int) -> ContentFile | None:
    """
    Read an uploaded image, optionally downscale, save as AVIF (if enabled) or WebP.

    Returns None to keep the original file (compression disabled, unsupported type, animated GIF, error).
    """
    if not getattr(settings, "IMAGE_AUTO_COMPRESS", True):
        return None

    try:
        file_obj.seek(0)
    except Exception:
        return None

    raw = file_obj.read()
    if not raw:
        return None

    out = compress_image_bytes(raw, max_side=max_side, respect_compress_setting=True)
    if out is None:
        return None
    data, ext = out
    name = f"{uuid.uuid4().hex}.{ext}"
    return ContentFile(data, name=name)


def compress_image_bytes(
    raw: bytes,
    *,
    max_side: int,
    respect_compress_setting: bool = True,
) -> tuple[bytes, str] | None:
    """
    Compress raw image bytes. Returns (data, extension_without_dot) or None.

    If respect_compress_setting is True and IMAGE_AUTO_COMPRESS is False, returns None.
    """
    if respect_compress_setting and not getattr(settings, "IMAGE_AUTO_COMPRESS", True):
        return None

    if not raw:
        return None

    q_webp = int(getattr(settings, "IMAGE_WEBP_QUALITY", 82))
    q_avif = int(getattr(settings, "IMAGE_AVIF_QUALITY", 70))
    try_avif = bool(getattr(settings, "IMAGE_TRY_AVIF", False))

    try:
        im = Image.open(io.BytesIO(raw))
        im.load()
    except (UnidentifiedImageError, OSError, ValueError):
        return None

    try:
        n_frames = getattr(im, "n_frames", 1)
    except Exception:
        n_frames = 1
    if n_frames > 1:
        return None

    try:
        im = ImageOps.exif_transpose(im)
    except Exception:
        pass

    w, h = im.size
    if w < 1 or h < 1:
        return None

    if max(w, h) > max_side:
        im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)

    if im.mode == "P":
        im = im.convert("RGBA" if "transparency" in im.info else "RGB")
    elif im.mode == "LA":
        im = im.convert("RGBA")
    elif im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGB")

    out = io.BytesIO()
    ext = "webp"

    def save_webp() -> None:
        out.seek(0)
        out.truncate(0)
        im.save(out, format="WEBP", quality=q_webp, method=4)

    if try_avif:
        try:
            out.seek(0)
            out.truncate(0)
            im.save(out, format="AVIF", quality=q_avif)
            ext = "avif"
        except Exception:
            try:
                save_webp()
                ext = "webp"
            except Exception:
                return None
    else:
        try:
            save_webp()
        except Exception:
            out.seek(0)
            out.truncate(0)
            try:
                im_flat = im
                if im_flat.mode == "RGBA":
                    bg = Image.new("RGB", im_flat.size, (255, 255, 255))
                    bg.paste(im_flat, mask=im_flat.split()[3])
                    im_flat = bg
                im_flat.save(out, format="JPEG", quality=88, optimize=True)
                ext = "jpg"
            except Exception:
                return None

    data = out.getvalue()
    if not data:
        return None
    return (data, ext)


def recompress_field_file(
    instance,
    field_name: str,
    *,
    max_side: int,
    dry_run: bool = False,
    skip_if_smaller_or_equal: bool = True,
    skip_modern_formats: bool = True,
) -> str:
    """
    Read stored ImageField from storage, recompress, replace file, update DB.

    Returns one of: 'ok', 'dry-run', 'skip', 'missing', 'error', 'no-op'.
    """
    ff = getattr(instance, field_name, None)
    if not ff or not ff.name:
        return "no-op"

    name_lower = ff.name.lower()
    if skip_modern_formats and (name_lower.endswith(".webp") or name_lower.endswith(".avif")):
        return "skip"

    storage = ff.storage
    if not storage.exists(ff.name):
        return "missing"

    try:
        with storage.open(ff.name, "rb") as f:
            raw = f.read()
    except Exception:
        return "error"

    if not raw:
        return "error"

    out = compress_image_bytes(raw, max_side=max_side, respect_compress_setting=False)
    if out is None:
        return "skip"

    new_data, ext = out
    if skip_if_smaller_or_equal and len(new_data) >= len(raw):
        return "skip"

    if dry_run:
        return "dry-run"

    old_name = ff.name
    new_cf = ContentFile(new_data, name=f"{uuid.uuid4().hex}.{ext}")
    getattr(instance, field_name).save(new_cf.name, new_cf, save=False)
    new_path = getattr(instance, field_name).name

    type(instance).objects.filter(pk=instance.pk).update(**{field_name: new_path})

    if old_name and old_name != new_path:
        try:
            storage.delete(old_name)
        except Exception:
            pass

    return "ok"
