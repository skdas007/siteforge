"""Dashboard views: login required, client-scoped; settings save to Client."""
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
            "whatsapp_number": getattr(client, "whatsapp_number", "") or "",
            "map_embed_url": getattr(client, "map_embed_url", "") or "",
            "seo_title": getattr(client, "seo_title", "") or "",
            "seo_description": getattr(client, "seo_description", "") or "",
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = self.request.user.client
        post = self.request.POST if self.request.method == "POST" else {}
        context["hero_title"] = post.get("hero_title") or client.hero_title or ""
        context["hero_subtitle"] = post.get("hero_subtitle") or client.hero_subtitle or ""
        context["theme_slug"] = post.get("theme") or (client.theme.slug if client.theme_id else "default")
        context["contact_email"] = post.get("contact_email") or client.contact_email or ""
        context["whatsapp_number"] = post.get("whatsapp_number") or getattr(client, "whatsapp_number", "") or ""
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
        else:
            context["seo_title"] = getattr(client, "seo_title", "") or ""
            context["seo_description"] = getattr(client, "seo_description", "") or ""
        context["seo_image_url"] = client.seo_image.url if getattr(client, "seo_image", None) and client.seo_image else None
        return context

    def form_valid(self, form):
        client = self.request.user.client
        client.refresh_from_db()
        client.hero_title = form.cleaned_data.get("hero_title", "")[:300]
        client.hero_subtitle = form.cleaned_data.get("hero_subtitle", "")
        client.contact_email = form.cleaned_data.get("contact_email", "") or ""
        client.whatsapp_number = (form.cleaned_data.get("whatsapp_number", "") or "").strip()[:20]
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
    return Product.objects.filter(client=request.user.client).select_related("category").order_by("order", "name")


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
        if extra_errors:
            for msg in extra_errors:
                form.add_error(None, msg)
            return self.form_invalid(form)
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
            "seo_image": None,
        }
        context["max_product_gallery_images"] = MAX_PRODUCT_GALLERY_IMAGES
        context["max_image_upload_bytes"] = MAX_IMAGE_UPLOAD_BYTES
        return context

    def form_valid(self, form):
        from apps.catalog.models import Product, ProductImage

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
            seo_image=form.cleaned_data.get("seo_image") or None,
            is_active=form.cleaned_data.get("is_active", True),
            is_main=form.cleaned_data.get("is_main", False),
            order=_get_product_queryset(self.request).count(),
        )
        for i, f in enumerate(self.request.FILES.getlist("extra_images") or []):
            if f and getattr(f, "content_type", "").startswith("image/"):
                ProductImage.objects.create(product=product, image=f, order=i)
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
        if extra_errors:
            for msg in extra_errors:
                form.add_error(None, msg)
            return self.form_invalid(form)
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
            "seo_image": product.seo_image.url if getattr(product, "seo_image", None) and product.seo_image else None,
            "is_active": product.is_active,
            "is_main": product.is_main,
            "extra_images": extra,
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
            "is_active": product.is_active,
            "is_main": product.is_main,
        }

    def form_valid(self, form):
        from apps.catalog.models import Product, ProductImage

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
        product.name = form.cleaned_data["name"]
        product.description = form.cleaned_data.get("description", "") or ""
        product.price = form.cleaned_data.get("price") or 0
        product.compare_at_price = form.cleaned_data.get("compare_at_price")
        product.category = form.cleaned_data.get("category") or None
        product.seo_title = (form.cleaned_data.get("seo_title", "") or "")[:200]
        product.seo_description = form.cleaned_data.get("seo_description", "") or ""
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


