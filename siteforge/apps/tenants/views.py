"""Dashboard views: login required, client-scoped; settings save to Client."""
import json
import re

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import FormView, ListView, TemplateView
from django.views.generic.edit import DeleteView

from apps.catalog.models import Category, Product
from apps.core.validators import MAX_IMAGE_UPLOAD_BYTES, MAX_VIDEO_UPLOAD_BYTES

from .forms import CategoryForm, ProductForm, SiteSettingsForm
from .mixins import DashboardClientMixin
from .models import CarouselSlide


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


def _validate_extra_product_images(request):
    """Return a list of error messages for additional product gallery uploads."""
    errors = []
    for i, f in enumerate(request.FILES.getlist("extra_images") or []):
        if not f:
            continue
        if not (getattr(f, "content_type", "") or "").startswith("image/"):
            errors.append(f"Additional image {i + 1}: upload an image file only.")
            continue
        if f.size > MAX_IMAGE_UPLOAD_BYTES:
            errors.append(f"Additional image {i + 1}: must be at most 3 MB.")
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
        from apps.themes.models import Theme
        themes = Theme.objects.filter(is_active=True).order_by("name")
        kwargs["theme_choices"] = [(t.slug, t.name) for t in themes]
        if not themes:
            kwargs["theme_choices"] = [("default", "Default"), ("minimal", "Minimal"), ("clarity", "Clarity")]
        return kwargs

    def get_initial(self):
        client = self.request.user.client
        return {
            "hero_title": client.hero_title or "",
            "hero_subtitle": client.hero_subtitle or "",
            "theme": client.theme.slug if client.theme_id else "default",
            "contact_email": client.contact_email or "",
            "whatsapp_number": getattr(client, "whatsapp_number", "") or "",
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
        return context

    def _delete_file_from_storage(self, file_field):
        """Remove file from S3/storage. Safe if missing."""
        if file_field:
            try:
                file_field.delete(save=False)
            except Exception:
                pass

    def form_valid(self, form):
        client = self.request.user.client
        client.hero_title = form.cleaned_data.get("hero_title", "")[:300]
        client.hero_subtitle = form.cleaned_data.get("hero_subtitle", "")
        client.contact_email = form.cleaned_data.get("contact_email", "") or ""
        client.whatsapp_number = (form.cleaned_data.get("whatsapp_number", "") or "").strip()[:20]

        # Banner: remove from S3 when cleared or replaced
        if self.request.POST.get("remove_banner"):
            self._delete_file_from_storage(client.banner_image)
            client.banner_image = None
        elif form.cleaned_data.get("banner_image"):
            self._delete_file_from_storage(client.banner_image)
            client.banner_image = form.cleaned_data["banner_image"]

        # Welcome / Hero image: remove from S3 when cleared or replaced
        if self.request.POST.get("remove_hero_image"):
            self._delete_file_from_storage(client.hero_image)
            client.hero_image = None
        elif form.cleaned_data.get("hero_image"):
            self._delete_file_from_storage(client.hero_image)
            client.hero_image = form.cleaned_data["hero_image"]

        # Logo: remove from S3 when cleared or replaced
        if self.request.POST.get("remove_logo"):
            self._delete_file_from_storage(client.logo)
            client.logo = None
        elif form.cleaned_data.get("logo"):
            self._delete_file_from_storage(client.logo)
            client.logo = form.cleaned_data["logo"]

        from apps.themes.models import Theme
        try:
            client.theme = Theme.objects.get(slug=form.cleaned_data.get("theme", "default"), is_active=True)
        except Theme.DoesNotExist:
            pass
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
        for i, pk in enumerate(order_ids):
            try:
                slide = qs.filter(pk=int(pk)).first()
                if slide and slide.order != i:
                    slide.order = i
                    slide.save(update_fields=["order"])
            except (ValueError, TypeError):
                pass
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
        context["product"] = {"extra_images": []}
        return context

    def form_valid(self, form):
        from apps.catalog.models import Product, ProductImage

        client = self.request.user.client
        product = Product.objects.create(
            client=client,
            name=form.cleaned_data["name"],
            description=form.cleaned_data.get("description", "") or "",
            price=form.cleaned_data.get("price") or 0,
            category=form.cleaned_data.get("category") or None,
            image=form.cleaned_data.get("image") or None,
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
            "image": product.image.url if product.image else None,
            "is_active": product.is_active,
            "is_main": product.is_main,
            "extra_images": extra,
        }
        return context

    def get_initial(self):
        product = get_object_or_404(_get_product_queryset(self.request), pk=self.kwargs["pk"])
        return {
            "name": product.name,
            "description": product.description or "",
            "price": product.price,
            "category": product.category,
            "is_active": product.is_active,
            "is_main": product.is_main,
        }

    def form_valid(self, form):
        from apps.catalog.models import Product, ProductImage

        product = get_object_or_404(_get_product_queryset(self.request), pk=self.kwargs["pk"])
        if form.cleaned_data.get("image"):
            if product.image:
                try:
                    product.image.delete(save=False)
                except Exception:
                    pass
            product.image = form.cleaned_data["image"]
        if self.request.POST.get("remove_product_image"):
            if product.image:
                try:
                    product.image.delete(save=False)
                except Exception:
                    pass
            product.image = None
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
        product.category = form.cleaned_data.get("category") or None
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
        id_to_index = {int(pk): i for i, pk in enumerate(order_ids)}
        for product in qs:
            new_order = id_to_index.get(product.pk)
            if new_order is not None and product.order != new_order:
                product.order = new_order
                product.save(update_fields=["order"])
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

    def form_valid(self, form):
        name = form.cleaned_data["name"].strip()
        if Category.objects.filter(client=self.request.user.client, name__iexact=name).exists():
            form.add_error("name", "A category with that name already exists.")
            return self.form_invalid(form)
        order = _get_category_queryset(self.request).count()
        Category.objects.create(client=self.request.user.client, name=name, order=order)
        messages.success(self.request, "Category added.")
        return redirect(self.success_url)


class CategoryDeleteView(DashboardClientMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        cat = get_object_or_404(_get_category_queryset(request), pk=self.kwargs["pk"])
        cat.delete()
        messages.success(request, "Category deleted.")
        return redirect("dashboard:category_list")


