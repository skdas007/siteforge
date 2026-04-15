"""Dashboard views: login required, client-scoped; settings save to Client."""
from decimal import Decimal, InvalidOperation
import json
import re

from urllib.parse import urlencode

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.dateparse import parse_date
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import FormView, ListView, TemplateView, UpdateView
from django.views.generic.edit import DeleteView

from apps.catalog.models import Category, Product
from apps.leads.models import ContactSubmission
from apps.core.storage_cleanup import delete_stored_file
from apps.core.validators import (
    MAX_IMAGE_UPLOAD_BYTES,
    MAX_PRODUCT_GALLERY_IMAGES,
    MAX_VIDEO_UPLOAD_BYTES,
)

from .forms import CategoryForm, ProductForm, SiteSettingsForm
from .mixins import DashboardClientMixin
from .models import CarouselSlide

BUILTIN_THEMES = [
    ("default", "Default"),
    ("minimal", "Minimal"),
    ("clarity", "Clarity (agency style + animations)"),
    ("aurora", "Aurora (colorful gradient)"),
    ("midnight", "Midnight (dark mode)"),
    ("blackred", "Black Red (bold contrast)"),
    ("emeraldgold", "Emerald Gold (premium)"),
]


class DashboardHomeView(DashboardClientMixin, TemplateView):
    template_name = "dashboard/home.html"


def _upload_is_video(f):
    if not f:
        return False
    ct = getattr(f, "content_type", "") or ""
    name = (getattr(f, "name", "") or "").lower()
    return ct.startswith("video/") or name.endswith(".mp4")


def _validate_carousel_uploads(request):
    """Return a list of error messages for oversized or invalid carousel files."""
    errors = []
    slides = _get_carousel_slides_from_request(request)
    for i, (f, _caption) in enumerate(slides):
        if not f:
            continue
        if _upload_is_video(f):
            if f.size > MAX_VIDEO_UPLOAD_BYTES:
                errors.append(
                    f"Carousel slide {i + 1}: video must be at most {MAX_VIDEO_UPLOAD_BYTES // (1024 * 1024)} MB."
                )
        else:
            if not (getattr(f, "content_type", "") or "").startswith("image/"):
                errors.append(
                    f"Carousel slide {i + 1}: upload an image or MP4 video only."
                )
                continue
            if f.size > MAX_IMAGE_UPLOAD_BYTES:
                errors.append(f"Carousel slide {i + 1}: image must be at most 3 MB.")
    return errors


def _validate_extra_product_images(request, *, existing_count: int = 0, removing_count: int = 0):
    """Return a list of error messages for additional product gallery uploads."""
    raw = [f for f in (request.FILES.getlist("extra_images") or []) if f]
    errors = []

    if len(raw) > MAX_PRODUCT_GALLERY_IMAGES:
        errors.append(
            f"Please select at most {MAX_PRODUCT_GALLERY_IMAGES} additional images at a time. "
            f"Save your product with up to {MAX_PRODUCT_GALLERY_IMAGES} gallery images, then use Edit to remove "
            "or replace images before adding more."
        )
        return errors

    new_files = []
    for i, f in enumerate(raw, start=1):
        if not (getattr(f, "content_type", "") or "").startswith("image/"):
            errors.append(f"Additional image {i}: upload an image file only.")
        else:
            new_files.append(f)
    if errors:
        return errors

    n_new = len(new_files)
    after_remove = max(0, existing_count - removing_count)
    if after_remove + n_new > MAX_PRODUCT_GALLERY_IMAGES:
        can_add = max(0, MAX_PRODUCT_GALLERY_IMAGES - after_remove)
        if can_add == 0:
            errors.append(
                f"This product already has {MAX_PRODUCT_GALLERY_IMAGES} additional gallery images (the maximum). "
                "Mark images with “Remove”, save, then add new ones — or choose at most "
                f"{MAX_PRODUCT_GALLERY_IMAGES} files when adding a new product."
            )
        else:
            errors.append(
                f"You can have at most {MAX_PRODUCT_GALLERY_IMAGES} additional gallery images per product. "
                f"After removals you can add {can_add} more here; you selected {n_new}. "
                "Upload fewer files, or save and edit again after removing some images."
            )
        return errors

    for i, f in enumerate(new_files, start=1):
        if f.size > MAX_IMAGE_UPLOAD_BYTES:
            errors.append(f"Additional image {i}: must be at most 3 MB.")
    return errors


def _extract_size_rows(post):
    labels = post.getlist("size_label")
    cms = post.getlist("size_cm")
    inches = post.getlist("size_inch")
    prices = post.getlist("size_price")
    compare_prices = post.getlist("size_compare_at_price")
    stocks = post.getlist("size_stock")
    row_count = max(len(labels), len(cms), len(inches), len(prices), len(compare_prices), len(stocks), 0)
    rows = []
    for i in range(row_count):
        rows.append(
            {
                "size_label": (labels[i] if i < len(labels) else "").strip(),
                "size_cm": (cms[i] if i < len(cms) else "").strip(),
                "size_inch": (inches[i] if i < len(inches) else "").strip(),
                "size_price": (prices[i] if i < len(prices) else "").strip(),
                "size_compare_at_price": (compare_prices[i] if i < len(compare_prices) else "").strip(),
                "size_stock": (stocks[i] if i < len(stocks) else "").strip(),
            }
        )
    return rows


def _validate_size_rows(post):
    cleaned = []
    errors = []
    rows = _extract_size_rows(post)
    seen = set()
    for idx, row in enumerate(rows, start=1):
        label = row["size_label"]
        cm = row["size_cm"]
        inch = row["size_inch"]
        price_raw = row["size_price"]
        compare_raw = row["size_compare_at_price"]
        stock_raw = row["size_stock"]
        if not (label or cm or inch or price_raw or compare_raw or stock_raw):
            continue
        if not label:
            errors.append(f"Size row {idx}: size label is required (e.g. M, L, XL).")
            continue
        key = label.lower()
        if key in seen:
            errors.append(f"Size row {idx}: duplicate size label '{label}'.")
            continue
        seen.add(key)
        if not price_raw:
            errors.append(f"Size row {idx}: price is required.")
            continue
        try:
            price = Decimal(price_raw)
        except (InvalidOperation, TypeError):
            errors.append(f"Size row {idx}: enter a valid price.")
            continue
        if price < 0:
            errors.append(f"Size row {idx}: price must be zero or more.")
            continue
        compare_price = None
        if compare_raw:
            try:
                compare_price = Decimal(compare_raw)
            except (InvalidOperation, TypeError):
                errors.append(f"Size row {idx}: enter a valid original price (MRP).")
                continue
            if compare_price < price:
                errors.append(f"Size row {idx}: original price (MRP) must be greater than or equal to sale price.")
                continue
        if stock_raw == "":
            stock_qty = 0
        else:
            try:
                stock_qty = int(stock_raw)
            except (TypeError, ValueError):
                errors.append(f"Size row {idx}: enter a valid stock quantity.")
                continue
            if stock_qty < 0:
                errors.append(f"Size row {idx}: stock quantity cannot be negative.")
                continue
        cleaned.append(
            {
                "size_label": label[:40],
                "measurement_cm": cm[:60],
                "measurement_inch": inch[:60],
                "price": price,
                "compare_at_price": compare_price,
                "stock_qty": stock_qty,
            }
        )
    return cleaned, errors


def _get_carousel_slides_from_request(request):
    """Extract carousel (image, caption) pairs from request.FILES and request.POST."""
    files = getattr(request, "FILES", {}) or {}
    post = getattr(request, "POST", {}) or {}
    indices = set()
    for key in files:
        m = re.match(r"carousel_image_(\d+)$", key)
        if m:
            indices.add(int(m.group(1)))
    for key in post:
        m = re.match(r"carousel_caption_(\d+)$", key)
        if m:
            indices.add(int(m.group(1)))
    result = []
    for i in sorted(indices):
        f = files.get(f"carousel_image_{i}")
        caption = (post.get(f"carousel_caption_{i}") or "").strip()[:200]
        result.append((f, caption))
    return result


def _ensure_builtin_themes():
    """
    Ensure built-in themes exist so dashboard radio options always persist on save.
    """
    from apps.themes.models import Theme

    for slug, name in BUILTIN_THEMES:
        Theme.objects.get_or_create(
            slug=slug,
            defaults={"name": name, "is_active": True},
        )


def _theme_choices():
    from apps.themes.models import Theme

    _ensure_builtin_themes()
    themes = Theme.objects.filter(is_active=True).order_by("name")
    if not themes.exists():
        return BUILTIN_THEMES
    return [(t.slug, t.name) for t in themes]


class DashboardSettingsView(DashboardClientMixin, FormView):
    """Site settings: load from and save to request.user.client."""
    form_class = SiteSettingsForm
    template_name = "dashboard/settings.html"
    success_url = reverse_lazy("dashboard:settings")

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if not form.is_valid():
            return self.form_invalid(form)
        carousel_errors = _validate_carousel_uploads(request)
        if carousel_errors:
            for msg in carousel_errors:
                form.add_error(None, msg)
            return self.form_invalid(form)
        return self.form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.method == "POST" and self.request.FILES:
            kwargs.setdefault("files", self.request.FILES)
        kwargs["theme_choices"] = _theme_choices()
        return kwargs

    def get_initial(self):
        client = self.request.user.client
        return {
            "hero_title": client.hero_title or "",
            "hero_subtitle": client.hero_subtitle or "",
            "theme": client.theme.slug if client.theme_id else "default",
            "contact_email": client.contact_email or "",
            "address_text": getattr(client, "address_text", "") or "",
            "whatsapp_number": getattr(client, "whatsapp_number", "") or "",
            "instagram_url": getattr(client, "instagram_url", "") or "",
            "facebook_url": getattr(client, "facebook_url", "") or "",
            "youtube_url": getattr(client, "youtube_url", "") or "",
            "map_embed_url": getattr(client, "map_embed_url", "") or "",
            "seo_title": getattr(client, "seo_title", "") or "",
            "seo_description": getattr(client, "seo_description", "") or "",
            "seo_keywords": getattr(client, "seo_keywords", "") or "",
            "seo_author": getattr(client, "seo_author", "") or "",
            "seo_robots": getattr(client, "seo_robots", "") or "index, follow",
            "seo_language": getattr(client, "seo_language", "") or "English",
            "seo_revisit_after": getattr(client, "seo_revisit_after", "") or "7 days",
            "seo_geo_region": getattr(client, "seo_geo_region", "") or "",
            "seo_geo_placename": getattr(client, "seo_geo_placename", "") or "",
            "seo_geo_position": getattr(client, "seo_geo_position", "") or "",
            "seo_icbm": getattr(client, "seo_icbm", "") or "",
            "seo_founder": getattr(client, "seo_founder", "") or "",
            "seo_address_locality": getattr(client, "seo_address_locality", "") or "",
            "seo_postal_code": getattr(client, "seo_postal_code", "") or "",
            "seo_address_region": getattr(client, "seo_address_region", "") or "",
            "seo_address_country": getattr(client, "seo_address_country", "") or "IN",
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = self.request.user.client
        post = self.request.POST if self.request.method == "POST" else {}
        context["hero_title"] = post.get("hero_title") or client.hero_title or ""
        context["hero_subtitle"] = post.get("hero_subtitle") or client.hero_subtitle or ""
        context["theme_slug"] = post.get("theme") or (client.theme.slug if client.theme_id else "default")
        context["contact_email"] = post.get("contact_email") or client.contact_email or ""
        context["address_text"] = post.get("address_text") or getattr(client, "address_text", "") or ""
        context["whatsapp_number"] = post.get("whatsapp_number") or getattr(client, "whatsapp_number", "") or ""
        context["instagram_url"] = post.get("instagram_url") or getattr(client, "instagram_url", "") or ""
        context["facebook_url"] = post.get("facebook_url") or getattr(client, "facebook_url", "") or ""
        context["youtube_url"] = post.get("youtube_url") or getattr(client, "youtube_url", "") or ""
        context["map_embed_url"] = post.get("map_embed_url") or getattr(client, "map_embed_url", "") or ""
        slides = CarouselSlide.objects.filter(client=client).order_by("order")
        context["existing_slides"] = [
            {
                "id": s.pk,
                "image_url": s.image.url if s.image else "",
                "video_url": s.video.url if s.video else "",
                "is_video": bool(s.video),
                "caption": s.caption or "",
            }
            for s in slides
        ]
        context["carousel_1_image_url"] = context["carousel_2_image_url"] = context["carousel_3_image_url"] = ""
        context["carousel_4_image_url"] = context["carousel_5_image_url"] = ""
        context["banner_image_url"] = client.banner_image.url if client.banner_image else None
        context["hero_image_url"] = client.hero_image.url if client.hero_image else None
        context["logo_url"] = client.logo.url if client.logo else None
        context["favicon_url_settings"] = client.favicon.url if client.favicon else None
        if self.request.method == "POST":
            context["seo_title"] = post.get("seo_title", "")
            context["seo_description"] = post.get("seo_description", "")
            context["seo_keywords"] = post.get("seo_keywords", "")
            context["seo_author"] = post.get("seo_author", "")
            context["seo_robots"] = post.get("seo_robots", "index, follow")
            context["seo_language"] = post.get("seo_language", "English")
            context["seo_revisit_after"] = post.get("seo_revisit_after", "7 days")
            context["seo_geo_region"] = post.get("seo_geo_region", "")
            context["seo_geo_placename"] = post.get("seo_geo_placename", "")
            context["seo_geo_position"] = post.get("seo_geo_position", "")
            context["seo_icbm"] = post.get("seo_icbm", "")
            context["seo_founder"] = post.get("seo_founder", "")
            context["seo_address_locality"] = post.get("seo_address_locality", "")
            context["seo_postal_code"] = post.get("seo_postal_code", "")
            context["seo_address_region"] = post.get("seo_address_region", "")
            context["seo_address_country"] = post.get("seo_address_country", "IN")
        else:
            context["seo_title"] = getattr(client, "seo_title", "") or ""
            context["seo_description"] = getattr(client, "seo_description", "") or ""
            context["seo_keywords"] = getattr(client, "seo_keywords", "") or ""
            context["seo_author"] = getattr(client, "seo_author", "") or ""
            context["seo_robots"] = getattr(client, "seo_robots", "") or "index, follow"
            context["seo_language"] = getattr(client, "seo_language", "") or "English"
            context["seo_revisit_after"] = getattr(client, "seo_revisit_after", "") or "7 days"
            context["seo_geo_region"] = getattr(client, "seo_geo_region", "") or ""
            context["seo_geo_placename"] = getattr(client, "seo_geo_placename", "") or ""
            context["seo_geo_position"] = getattr(client, "seo_geo_position", "") or ""
            context["seo_icbm"] = getattr(client, "seo_icbm", "") or ""
            context["seo_founder"] = getattr(client, "seo_founder", "") or ""
            context["seo_address_locality"] = getattr(client, "seo_address_locality", "") or ""
            context["seo_postal_code"] = getattr(client, "seo_postal_code", "") or ""
            context["seo_address_region"] = getattr(client, "seo_address_region", "") or ""
            context["seo_address_country"] = getattr(client, "seo_address_country", "") or "IN"
        context["seo_image_url"] = client.seo_image.url if getattr(client, "seo_image", None) and client.seo_image else None
        return context

    def form_valid(self, form):
        client = self.request.user.client
        client.refresh_from_db()
        client.hero_title = form.cleaned_data.get("hero_title", "")[:300]
        client.hero_subtitle = form.cleaned_data.get("hero_subtitle", "")
        client.contact_email = form.cleaned_data.get("contact_email", "") or ""
        client.address_text = form.cleaned_data.get("address_text", "") or ""
        client.whatsapp_number = (form.cleaned_data.get("whatsapp_number", "") or "").strip()[:20]
        client.instagram_url = form.cleaned_data.get("instagram_url", "") or ""
        client.facebook_url = form.cleaned_data.get("facebook_url", "") or ""
        client.youtube_url = form.cleaned_data.get("youtube_url", "") or ""
        client.map_embed_url = (form.cleaned_data.get("map_embed_url", "") or "").strip()[:1200]

        # Prefer new upload over "remove" so replace-by-file-picker deletes the old S3 object.
        # Banner
        if form.cleaned_data.get("banner_image"):
            delete_stored_file(client.banner_image)
            client.banner_image = form.cleaned_data["banner_image"]
        elif self.request.POST.get("remove_banner"):
            delete_stored_file(client.banner_image)
            client.banner_image = None

        # Welcome / Hero image
        if form.cleaned_data.get("hero_image"):
            delete_stored_file(client.hero_image)
            client.hero_image = form.cleaned_data["hero_image"]
        elif self.request.POST.get("remove_hero_image"):
            delete_stored_file(client.hero_image)
            client.hero_image = None

        # Logo
        if form.cleaned_data.get("logo"):
            delete_stored_file(client.logo)
            client.logo = form.cleaned_data["logo"]
        elif self.request.POST.get("remove_logo"):
            delete_stored_file(client.logo)
            client.logo = None

        if form.cleaned_data.get("favicon"):
            delete_stored_file(getattr(client, "favicon", None))
            client.favicon = form.cleaned_data["favicon"]
        elif self.request.POST.get("remove_favicon"):
            delete_stored_file(getattr(client, "favicon", None))
            client.favicon = None

        client.seo_title = (form.cleaned_data.get("seo_title", "") or "")[:200]
        client.seo_description = form.cleaned_data.get("seo_description", "") or ""
        client.seo_keywords = form.cleaned_data.get("seo_keywords", "") or ""
        client.seo_author = (form.cleaned_data.get("seo_author", "") or "")[:200]
        client.seo_robots = (form.cleaned_data.get("seo_robots", "") or "index, follow")[:40]
        client.seo_language = (form.cleaned_data.get("seo_language", "") or "English")[:40]
        client.seo_revisit_after = (form.cleaned_data.get("seo_revisit_after", "") or "7 days")[:40]
        client.seo_geo_region = (form.cleaned_data.get("seo_geo_region", "") or "")[:24]
        client.seo_geo_placename = (form.cleaned_data.get("seo_geo_placename", "") or "")[:120]
        client.seo_geo_position = (form.cleaned_data.get("seo_geo_position", "") or "")[:50]
        client.seo_icbm = (form.cleaned_data.get("seo_icbm", "") or "")[:50]
        client.seo_founder = (form.cleaned_data.get("seo_founder", "") or "")[:120]
        client.seo_address_locality = (form.cleaned_data.get("seo_address_locality", "") or "")[:120]
        client.seo_postal_code = (form.cleaned_data.get("seo_postal_code", "") or "")[:20]
        client.seo_address_region = (form.cleaned_data.get("seo_address_region", "") or "")[:120]
        client.seo_address_country = (form.cleaned_data.get("seo_address_country", "") or "IN")[:10]
        if form.cleaned_data.get("seo_image"):
            delete_stored_file(getattr(client, "seo_image", None))
            client.seo_image = form.cleaned_data["seo_image"]
        elif self.request.POST.get("remove_seo_image"):
            delete_stored_file(getattr(client, "seo_image", None))
            client.seo_image = None

        from apps.themes.models import Theme
        _ensure_builtin_themes()
        try:
            client.theme = Theme.objects.get(slug=form.cleaned_data.get("theme", "default"), is_active=True)
        except Theme.DoesNotExist:
            fallback_slug = "default"
            client.theme = Theme.objects.filter(slug=fallback_slug, is_active=True).first()
        client.save()

        # Save carousel: update kept slides in place; add new; delete removed (post_delete deletes file from S3)
        slides_from_request = _get_carousel_slides_from_request(self.request)
        existing = list(CarouselSlide.objects.filter(client=client).order_by("order"))
        for i, (new_file, caption) in enumerate(slides_from_request):
            cap = (caption or "")[:200]
            if new_file:
                if i < len(existing):
                    existing[i].delete()  # signal deletes image/video from storage
                if _upload_is_video(new_file):
                    CarouselSlide.objects.create(client=client, video=new_file, caption=cap, order=i)
                else:
                    CarouselSlide.objects.create(client=client, image=new_file, caption=cap, order=i)
            elif i < len(existing):
                existing[i].caption = cap
                existing[i].order = i
                existing[i].save()
        for j in range(len(slides_from_request), len(existing)):
            existing[j].delete()  # signal deletes image/video from storage

        messages.success(self.request, "Settings saved.")
        return redirect(self.success_url)


def _get_carousel_slides_queryset(request):
    return CarouselSlide.objects.filter(client=request.user.client).order_by("order")


class CarouselReorderView(DashboardClientMixin, View):
    """POST JSON {\"order\": [id, ...]} to update carousel slide order."""
    http_method_names = ["post"]

    def post(self, request):
        try:
            data = json.loads(request.body or "{}")
            order_ids = data.get("order")
        except (json.JSONDecodeError, TypeError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        if not isinstance(order_ids, list):
            return JsonResponse({"error": "order must be a list"}, status=400)
        qs = _get_carousel_slides_queryset(request)
        valid_ids = set(qs.values_list("pk", flat=True))
        given_ids = set(int(x) for x in order_ids if isinstance(x, (int, str)) and str(x).isdigit())
        if given_ids != valid_ids:
            return JsonResponse({"error": "Order must contain exactly your slide IDs"}, status=400)
        # QuerySet.update avoids model save()/full_clean() — file fields must not hit storage on reorder.
        with transaction.atomic():
            for new_order, raw_id in enumerate(order_ids):
                try:
                    pk = int(raw_id)
                except (ValueError, TypeError):
                    continue
                qs.filter(pk=pk).update(order=new_order)
        return JsonResponse({"ok": True})


def _get_category_queryset(request):
    return Category.objects.filter(client=request.user.client).order_by("order", "name")


def _get_product_queryset(request):
    return (
        Product.objects.filter(client=request.user.client)
        .select_related("category")
        .prefetch_related("size_variants")
        .order_by("order", "name")
    )


class ProductListView(DashboardClientMixin, ListView):
    template_name = "dashboard/product_list.html"
    context_object_name = "products"

    def get_queryset(self):
        return _get_product_queryset(self.request)


class ProductAddView(DashboardClientMixin, FormView):
    form_class = ProductForm
    template_name = "dashboard/product_form.html"
    success_url = reverse_lazy("dashboard:product_list")

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if not form.is_valid():
            return self.form_invalid(form)
        extra_errors = _validate_extra_product_images(request)
        size_rows, size_errors = _validate_size_rows(request.POST)
        if extra_errors:
            for msg in extra_errors:
                form.add_error(None, msg)
        if size_errors:
            for msg in size_errors:
                form.add_error(None, msg)
        if extra_errors or size_errors:
            return self.form_invalid(form)
        request._validated_size_rows = size_rows
        return self.form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.setdefault("category_queryset", _get_category_queryset(self.request))
        if self.request.method == "POST" and self.request.FILES:
            kwargs.setdefault("files", self.request.FILES)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_title"] = "Add product"
        context["form_action"] = reverse("dashboard:product_add")
        context["product"] = {
            "extra_images": [],
            "seo_title": "",
            "seo_description": "",
            "seo_keywords": "",
            "seo_image": None,
            "size_rows": _extract_size_rows(self.request.POST) if self.request.method == "POST" else [{}],
        }
        context["max_product_gallery_images"] = MAX_PRODUCT_GALLERY_IMAGES
        context["max_image_upload_bytes"] = MAX_IMAGE_UPLOAD_BYTES
        return context

    def form_valid(self, form):
        from apps.catalog.models import Product, ProductImage, ProductSizeVariant

        client = self.request.user.client
        product = Product.objects.create(
            client=client,
            name=form.cleaned_data["name"],
            description=form.cleaned_data.get("description", "") or "",
            price=form.cleaned_data.get("price") or 0,
            compare_at_price=form.cleaned_data.get("compare_at_price"),
            category=form.cleaned_data.get("category") or None,
            image=form.cleaned_data.get("image") or None,
            seo_title=(form.cleaned_data.get("seo_title", "") or "")[:200],
            seo_description=form.cleaned_data.get("seo_description", "") or "",
            seo_keywords=form.cleaned_data.get("seo_keywords", "") or "",
            seo_image=form.cleaned_data.get("seo_image") or None,
            is_active=form.cleaned_data.get("is_active", True),
            is_main=form.cleaned_data.get("is_main", False),
            order=_get_product_queryset(self.request).count(),
        )
        for i, f in enumerate(self.request.FILES.getlist("extra_images") or []):
            if f and getattr(f, "content_type", "").startswith("image/"):
                ProductImage.objects.create(product=product, image=f, order=i)
        size_rows = getattr(self.request, "_validated_size_rows", None)
        if size_rows is None:
            size_rows, _ = _validate_size_rows(self.request.POST)
        for i, row in enumerate(size_rows):
            ProductSizeVariant.objects.create(
                product=product,
                order=i,
                size_label=row["size_label"],
                measurement_cm=row["measurement_cm"],
                measurement_inch=row["measurement_inch"],
                price=row["price"],
                compare_at_price=row["compare_at_price"],
                stock_qty=row["stock_qty"],
            )
        messages.success(self.request, "Product added.")
        return redirect(self.success_url)


class ProductEditView(DashboardClientMixin, FormView):
    form_class = ProductForm
    template_name = "dashboard/product_form.html"
    success_url = reverse_lazy("dashboard:product_list")

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if not form.is_valid():
            return self.form_invalid(form)
        product = get_object_or_404(_get_product_queryset(request), pk=self.kwargs["pk"])
        remove_pks = []
        for pk in request.POST.getlist("remove_extra_image"):
            try:
                remove_pks.append(int(pk))
            except (ValueError, TypeError):
                pass
        removing_count = product.extra_images.filter(pk__in=remove_pks).count()
        extra_errors = _validate_extra_product_images(
            request,
            existing_count=product.extra_images.count(),
            removing_count=removing_count,
        )
        size_rows, size_errors = _validate_size_rows(request.POST)
        if extra_errors:
            for msg in extra_errors:
                form.add_error(None, msg)
        if size_errors:
            for msg in size_errors:
                form.add_error(None, msg)
        if extra_errors or size_errors:
            return self.form_invalid(form)
        request._validated_size_rows = size_rows
        return self.form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.setdefault("category_queryset", _get_category_queryset(self.request))
        if self.request.method == "POST" and self.request.FILES:
            kwargs.setdefault("files", self.request.FILES)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = get_object_or_404(_get_product_queryset(self.request), pk=self.kwargs["pk"])
        extra = [
            {"id": pi.pk, "url": pi.image.url}
            for pi in product.extra_images.all()
        ]
        context["form_title"] = "Edit product"
        context["form_action"] = reverse("dashboard:product_edit", kwargs={"pk": product.pk})
        context["product"] = {
            "id": product.pk,
            "name": product.name,
            "description": product.description or "",
            "price": product.price,
            "compare_at_price": product.compare_at_price,
            "image": product.image.url if product.image else None,
            "seo_title": getattr(product, "seo_title", "") or "",
            "seo_description": getattr(product, "seo_description", "") or "",
            "seo_keywords": getattr(product, "seo_keywords", "") or "",
            "seo_image": product.seo_image.url if getattr(product, "seo_image", None) and product.seo_image else None,
            "is_active": product.is_active,
            "is_main": product.is_main,
            "extra_images": extra,
            "size_rows": (
                _extract_size_rows(self.request.POST)
                if self.request.method == "POST"
                else [
                    {
                        "size_label": s.size_label,
                        "size_cm": s.measurement_cm,
                        "size_inch": s.measurement_inch,
                        "size_price": s.price,
                        "size_compare_at_price": s.compare_at_price,
                        "size_stock": s.stock_qty,
                    }
                    for s in product.size_variants.all()
                ]
                or [{}]
            ),
        }
        context["max_product_gallery_images"] = MAX_PRODUCT_GALLERY_IMAGES
        context["max_image_upload_bytes"] = MAX_IMAGE_UPLOAD_BYTES
        return context

    def get_initial(self):
        product = get_object_or_404(_get_product_queryset(self.request), pk=self.kwargs["pk"])
        return {
            "name": product.name,
            "description": product.description or "",
            "price": product.price,
            "compare_at_price": product.compare_at_price,
            "category": product.category,
            "seo_title": getattr(product, "seo_title", "") or "",
            "seo_description": getattr(product, "seo_description", "") or "",
            "seo_keywords": getattr(product, "seo_keywords", "") or "",
            "is_active": product.is_active,
            "is_main": product.is_main,
        }

    def form_valid(self, form):
        from apps.catalog.models import Product, ProductImage, ProductSizeVariant

        product = get_object_or_404(_get_product_queryset(self.request), pk=self.kwargs["pk"])
        product.refresh_from_db()
        if form.cleaned_data.get("image"):
            delete_stored_file(product.image)
            product.image = form.cleaned_data["image"]
        elif self.request.POST.get("remove_product_image"):
            delete_stored_file(product.image)
            product.image = None
        if form.cleaned_data.get("seo_image"):
            delete_stored_file(getattr(product, "seo_image", None))
            product.seo_image = form.cleaned_data["seo_image"]
        elif self.request.POST.get("remove_product_seo_image"):
            delete_stored_file(getattr(product, "seo_image", None))
            product.seo_image = None
        for pk in self.request.POST.getlist("remove_extra_image") or []:
            try:
                pi = product.extra_images.filter(pk=int(pk)).first()
                if pi:
                    pi.delete()
            except (ValueError, TypeError):
                pass
        start_order = product.extra_images.count()
        for i, f in enumerate(self.request.FILES.getlist("extra_images") or []):
            if f and getattr(f, "content_type", "").startswith("image/"):
                ProductImage.objects.create(product=product, image=f, order=start_order + i)
        size_rows = getattr(self.request, "_validated_size_rows", None)
        if size_rows is None:
            size_rows, _ = _validate_size_rows(self.request.POST)
        product.size_variants.all().delete()
        for i, row in enumerate(size_rows):
            ProductSizeVariant.objects.create(
                product=product,
                order=i,
                size_label=row["size_label"],
                measurement_cm=row["measurement_cm"],
                measurement_inch=row["measurement_inch"],
                price=row["price"],
                compare_at_price=row["compare_at_price"],
                stock_qty=row["stock_qty"],
            )
        product.name = form.cleaned_data["name"]
        product.description = form.cleaned_data.get("description", "") or ""
        product.price = form.cleaned_data.get("price") or 0
        product.compare_at_price = form.cleaned_data.get("compare_at_price")
        product.category = form.cleaned_data.get("category") or None
        product.seo_title = (form.cleaned_data.get("seo_title", "") or "")[:200]
        product.seo_description = form.cleaned_data.get("seo_description", "") or ""
        product.seo_keywords = form.cleaned_data.get("seo_keywords", "") or ""
        product.is_active = form.cleaned_data.get("is_active", True)
        product.is_main = form.cleaned_data.get("is_main", False)
        product.save()
        messages.success(self.request, "Product updated.")
        return redirect(self.success_url)


class ProductDeleteView(DashboardClientMixin, DeleteView):
    """Delete product; image removed via catalog signal."""
    model = Product
    success_url = reverse_lazy("dashboard:product_list")
    context_object_name = "product"
    template_name = "dashboard/product_confirm_delete.html"

    def get_queryset(self):
        return _get_product_queryset(self.request)

    def form_valid(self, form):
        messages.success(self.request, "Product deleted.")
        return super().form_valid(form)


class ProductReorderView(DashboardClientMixin, View):
    """Accept POST JSON { \"order\": [id, ...] } and update product order for the client."""
    http_method_names = ["post"]

    def post(self, request):
        try:
            data = json.loads(request.body or "{}")
            order_ids = data.get("order")
        except (json.JSONDecodeError, TypeError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        if not isinstance(order_ids, list):
            return JsonResponse({"error": "order must be a list"}, status=400)
        qs = _get_product_queryset(request)
        valid_ids = set(qs.values_list("pk", flat=True))
        given_ids = set(int(x) for x in order_ids if isinstance(x, (int, str)) and str(x).isdigit())
        if given_ids != valid_ids:
            return JsonResponse({"error": "Order must contain exactly your product IDs"}, status=400)
        # QuerySet.update avoids Product.save() → full_clean(); missing S3 objects would 500 on ImageField.size.
        with transaction.atomic():
            for new_order, raw_id in enumerate(order_ids):
                try:
                    pk = int(raw_id)
                except (ValueError, TypeError):
                    continue
                qs.filter(pk=pk).update(order=new_order)
        return JsonResponse({"ok": True})


class CategoryListView(DashboardClientMixin, ListView):
    template_name = "dashboard/category_list.html"
    context_object_name = "categories"

    def get_queryset(self):
        return _get_category_queryset(self.request)


class CategoryCreateView(DashboardClientMixin, FormView):
    form_class = CategoryForm
    template_name = "dashboard/category_form.html"
    success_url = reverse_lazy("dashboard:category_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["client"] = self.request.user.client
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form_title"] = "Add category"
        ctx["is_edit"] = False
        return ctx

    def form_valid(self, form):
        cat = form.save(commit=False)
        cat.client = self.request.user.client
        cat.order = _get_category_queryset(self.request).count()
        cat.save()
        messages.success(self.request, "Category added.")
        return redirect(self.success_url)


class CategoryEditView(DashboardClientMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "dashboard/category_form.html"
    success_url = reverse_lazy("dashboard:category_list")

    def get_queryset(self):
        return _get_category_queryset(self.request)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["client"] = self.request.user.client
        kwargs["editing_pk"] = self.object.pk
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form_title"] = "Edit category"
        ctx["is_edit"] = True
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Category updated.")
        return super().form_valid(form)


class CategoryDeleteView(DashboardClientMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        cat = get_object_or_404(_get_category_queryset(request), pk=self.kwargs["pk"])
        cat.delete()
        messages.success(request, "Category deleted.")
        return redirect("dashboard:category_list")


def _get_contact_submission_queryset(request):
    return ContactSubmission.objects.filter(client=request.user.client).order_by("-created_at")


class ContactSubmissionListView(DashboardClientMixin, ListView):
    """Paginated contact form submissions for the logged-in client's site."""

    model = ContactSubmission
    template_name = "dashboard/contact_submissions.html"
    context_object_name = "submissions"
    paginate_by = 20

    def get_queryset(self):
        qs = _get_contact_submission_queryset(self.request)
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(email__icontains=q)
                | Q(phone__icontains=q)
                | Q(message__icontains=q)
            )
        df = (self.request.GET.get("date_from") or "").strip()
        dt = (self.request.GET.get("date_to") or "").strip()
        d_from = parse_date(df) if df else None
        d_to = parse_date(dt) if dt else None
        if d_from:
            qs = qs.filter(created_at__date__gte=d_from)
        if d_to:
            qs = qs.filter(created_at__date__lte=d_to)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter_q"] = (self.request.GET.get("q") or "").strip()
        ctx["filter_date_from"] = (self.request.GET.get("date_from") or "").strip()
        ctx["filter_date_to"] = (self.request.GET.get("date_to") or "").strip()
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["filter_querystring"] = urlencode(params)
        return ctx


class ContactSubmissionDeleteView(DashboardClientMixin, DeleteView):
    model = ContactSubmission
    template_name = "dashboard/contact_submission_confirm_delete.html"
    context_object_name = "submission"
    success_url = reverse_lazy("dashboard:contact_list")

    def get_queryset(self):
        return _get_contact_submission_queryset(self.request)

    def form_valid(self, form):
        messages.success(self.request, "Contact message deleted.")
        return super().form_valid(form)


class ContactSubmissionBulkDeleteView(DashboardClientMixin, View):
    """POST: delete selected contact rows (current client only)."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        raw_ids = request.POST.getlist("submission_ids")
        ids = []
        for x in raw_ids:
            try:
                ids.append(int(x))
            except (ValueError, TypeError):
                continue
        if not ids:
            messages.warning(request, "No messages selected.")
            return redirect(self._return_list_url(request))

        qs = _get_contact_submission_queryset(request).filter(pk__in=ids)
        deleted, _ = qs.delete()
        if deleted:
            messages.success(
                request,
                f"Deleted {deleted} message{'s' if deleted != 1 else ''}.",
            )
        return redirect(self._return_list_url(request))

    def _return_list_url(self, request):
        """Rebuild contact list URL with optional filters/page from POST (same keys as GET)."""
        params = {}
        q = (request.POST.get("q") or "").strip()
        if q:
            params["q"] = q
        df = (request.POST.get("date_from") or "").strip()
        if df:
            params["date_from"] = df
        dt = (request.POST.get("date_to") or "").strip()
        if dt:
            params["date_to"] = dt
        page = (request.POST.get("page") or "").strip()
        if page.isdigit() and int(page) > 1:
            params["page"] = page
        base = reverse("dashboard:contact_list")
        if params:
            return f"{base}?{urlencode(params)}"
        return base


