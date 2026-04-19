import json
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.sitemaps.views import sitemap as sitemap_index_view
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import F, Min
from django.db.models.functions import Coalesce
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.templatetags.static import static
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView

from apps.core.seo_utils import (
    absolute_media_url,
    add_seo_context,
    client_site_og_image_url,
    plain_text_excerpt,
    product_og_image_url,
)
from apps.core.sitemaps import TenantPublicSitemap

HOME_PRODUCTS_PER_PAGE = 6
PRODUCT_LIST_PER_PAGE = 9
FONT_META = {
    "inter": {"family": "Inter", "css": '"Inter", system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif', "google": "Inter:wght@400;500;600;700"},
    "poppins": {"family": "Poppins", "css": '"Poppins", system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif', "google": "Poppins:wght@400;500;600;700"},
    "dm-sans": {"family": "DM Sans", "css": '"DM Sans", system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif', "google": "DM+Sans:wght@400;500;700"},
    "lato": {"family": "Lato", "css": '"Lato", "Helvetica Neue", Arial, sans-serif', "google": "Lato:wght@400;700"},
    "roboto": {"family": "Roboto", "css": '"Roboto", "Helvetica Neue", Arial, sans-serif', "google": "Roboto:wght@400;500;700"},
    "playfair": {"family": "Playfair Display", "css": '"Playfair Display", Georgia, "Times New Roman", serif', "google": "Playfair+Display:wght@500;600;700"},
    "cormorant": {"family": "Cormorant Garamond", "css": '"Cormorant Garamond", Georgia, "Times New Roman", serif', "google": "Cormorant+Garamond:wght@500;600;700"},
}

from .forms import ContactForm, OptionalPhoneForm


def _parse_price_filter_param(raw):
    """Parse ?min_price= / ?max_price= query values (decimals, commas ok)."""
    if raw is None:
        return None
    s = str(raw).strip().replace(",", ".").replace(" ", "")
    if not s:
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError, TypeError):
        return None


def _product_queryset_filter_by_price_range(qs, request_get):
    """
    Filter by min/max against the storefront list price: lowest variant price when size
    variants exist, otherwise Product.price (matches Product.display_price).
    """
    min_p = _parse_price_filter_param(request_get.get("min_price"))
    max_p = _parse_price_filter_param(request_get.get("max_price"))
    if min_p is None and max_p is None:
        return qs
    qs = qs.annotate(_effective_list_price=Coalesce(Min("size_variants__price"), F("price")))
    if min_p is not None:
        qs = qs.filter(_effective_list_price__gte=min_p)
    if max_p is not None:
        qs = qs.filter(_effective_list_price__lte=max_p)
    return qs


def _whatsapp_product_inquiry_message(request, product):
    """
    Pre-filled WhatsApp message so the seller sees product name, price, public URL, and ID.
    """
    product_url = request.build_absolute_uri(reverse("product_detail", kwargs={"pk": product.pk}))
    name = str(product.name).replace("\r", " ").replace("\n", " ").strip()
    lines = [
        "Hi! I'm interested in this product from your website:",
        "",
        f"Product: {name}",
    ]
    price = getattr(product, "display_price", None)
    if price is not None:
        lines.append(f"Price: {price}")
    cat = getattr(product, "category", None)
    if cat is not None:
        lines.append(f"Category: {cat.name}")
    lines.extend(
        [
            "",
            f"Product page: {product_url}",
            f"Product ID: {product.pk}",
            "",
            "Please let me know availability and how to order. Thank you!",
        ]
    )
    return "\n".join(lines)


def _client_context(request, *, include_catalog_data=True):
    """Build template context from request.client when set (multi-tenant)."""
    from apps.catalog.models import Category, Product
    from apps.tenants.models import CarouselSlide, LegalPage

    client = getattr(request, "client", None)
    if not client:
        return {}
    slides = CarouselSlide.objects.filter(client=client).order_by("order")
    slider_slides = []
    for s in slides:
        if s.video:
            slider_slides.append({"media_type": "video", "image": None, "video": s.video.url, "caption": s.caption or ""})
        elif s.image:
            slider_slides.append({"media_type": "image", "image": s.image.url, "video": None, "caption": s.caption or ""})
    if not slider_slides:
        slider_slides = None
    products = None
    main_product = None
    spotlight_categories = []
    if include_catalog_data:
        products = Product.objects.filter(client=client, is_active=True).prefetch_related("size_variants").order_by(
            "order", "name"
        )
        main_product = products.order_by("-is_main", "order", "name").first()
        spotlight_categories = list(
            Category.objects.filter(client=client, show_in_spotlight=True).order_by(
                "spotlight_order", "order", "pk"
            )[:4]
        )
    legal_pages_footer = list(
        LegalPage.objects.filter(client=client, is_active=True, show_in_footer=True)
        .order_by("order", "title", "pk")
        .values("title", "slug")
    )
    now = timezone.now()
    popup_start = getattr(client, "popup_start_at", None)
    popup_end = getattr(client, "popup_end_at", None)
    popup_is_active = bool(getattr(client, "popup_enabled", False))
    if popup_is_active and popup_start and now < popup_start:
        popup_is_active = False
    if popup_is_active and popup_end and now > popup_end:
        popup_is_active = False

    def _safe_hex(value, fallback):
        v = (value or "").strip()
        if len(v) == 7 and v.startswith("#"):
            body = v[1:]
            if all(c in "0123456789abcdefABCDEF" for c in body):
                return v
        return fallback

    body_font_key = (getattr(client, "font_body", "") or "inter").strip().lower()
    heading_font_key = (getattr(client, "font_heading", "") or "poppins").strip().lower()
    if body_font_key not in FONT_META:
        body_font_key = "inter"
    if heading_font_key not in FONT_META:
        heading_font_key = "poppins"
    google_families = {
        FONT_META[body_font_key]["google"],
        FONT_META[heading_font_key]["google"],
    }

    return {
        "theme_slug": client.theme_slug,
        "business_name": client.business_name,
        "banner_image": client.banner_image.url if client.banner_image else None,
        "hero_image": client.hero_image.url if client.hero_image else None,
        "logo": client.logo.url if client.logo else None,
        "hero_title": client.hero_title or "Welcome",
        "hero_subtitle": client.hero_subtitle or "Your tagline or short description goes here.",
        "contact_email": client.contact_email,
        "footer_intro": getattr(client, "footer_intro", "") or "",
        "address_text": getattr(client, "address_text", "") or "",
        "whatsapp_number": (getattr(client, "whatsapp_number", "") or "").strip(),
        "whatsapp_digits": "".join(c for c in (getattr(client, "whatsapp_number", "") or "") if c.isdigit()),
        "instagram_url": getattr(client, "instagram_url", "") or "",
        "facebook_url": getattr(client, "facebook_url", "") or "",
        "youtube_url": getattr(client, "youtube_url", "") or "",
        "map_embed_url": getattr(client, "map_embed_url", None),
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
        "slider_slides": slider_slides,
        "main_product": main_product,
        "products": products,
        "spotlight_categories": spotlight_categories,
        "legal_pages_footer": legal_pages_footer,
        "announcement_enabled": bool(getattr(client, "announcement_enabled", False)) and bool(
            (getattr(client, "announcement_text", "") or "").strip()
        ),
        "announcement_text": getattr(client, "announcement_text", "") or "",
        "announcement_cta_label": getattr(client, "announcement_cta_label", "") or "",
        "announcement_cta_url": getattr(client, "announcement_cta_url", "") or "",
        "announcement_bg_color": _safe_hex(getattr(client, "announcement_bg_color", ""), "#0d6efd"),
        "announcement_text_color": _safe_hex(getattr(client, "announcement_text_color", ""), "#ffffff"),
        "popup_enabled": popup_is_active,
        "popup_title": getattr(client, "popup_title", "") or "",
        "popup_message": getattr(client, "popup_message", "") or "",
        "popup_image_url": client.popup_image.url if getattr(client, "popup_image", None) and client.popup_image else "",
        "popup_cta_label": getattr(client, "popup_cta_label", "") or "",
        "popup_cta_url": getattr(client, "popup_cta_url", "") or "",
        "popup_show_rule": getattr(client, "popup_show_rule", "") or "session",
        "popup_seen_key": f"{client.pk}-{int(client.updated_at.timestamp()) if getattr(client, 'updated_at', None) else client.pk}",
        "font_body_key": body_font_key,
        "font_heading_key": heading_font_key,
        "font_body_css": FONT_META[body_font_key]["css"],
        "font_heading_css": FONT_META[heading_font_key]["css"],
        "font_google_families": "|".join(sorted(google_families)),
    }


class IndexView(TemplateView):
    """Public home: banner, hero, products, contact form. Uses request.client when set by TenantResolutionMiddleware."""
    template_name = "public/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Search: ?q= filters home product grid (name / description).
        context.setdefault("search_query", (self.request.GET.get("q") or "").strip())
        # Query param ?theme= for preview overrides
        q = self.request.GET.get("theme")
        if q in ("default", "minimal", "clarity", "aurora", "midnight", "blackred", "emeraldgold"):
            context["theme_slug"] = q
            _empty = Paginator([], HOME_PRODUCTS_PER_PAGE)
            context["products"] = _empty.page(1)
            context["home_products_total_count"] = 0
            context["spotlight_categories"] = []
        elif getattr(self.request, "client", None):
            from apps.catalog.models import Category

            ctx = _client_context(self.request)
            for k, v in ctx.items():
                context.setdefault(k, v)
            context.setdefault("categories", Category.objects.filter(client=self.request.client).order_by("order", "name"))
            try:
                context["current_category_id"] = int(self.request.GET.get("category"))
            except (TypeError, ValueError):
                context["current_category_id"] = None
            if context.get("current_category_id"):
                context["products"] = context["products"].filter(category_id=context["current_category_id"])
            products_qs = context["products"]
            sq = (self.request.GET.get("q") or "").strip()
            context["search_query"] = sq
            if sq:
                from django.db.models import Q

                products_qs = products_qs.filter(Q(name__icontains=sq) | Q(description__icontains=sq))
            products_qs = _product_queryset_filter_by_price_range(products_qs, self.request.GET)
            context["home_products_total_count"] = products_qs.count()
            paginator = Paginator(products_qs, HOME_PRODUCTS_PER_PAGE)
            raw_page = self.request.GET.get("page") or 1
            try:
                context["products"] = paginator.page(raw_page)
            except PageNotAnInteger:
                context["products"] = paginator.page(1)
            except EmptyPage:
                context["products"] = paginator.page(paginator.num_pages)
        else:
            context.setdefault("theme_slug", "default")
            context.setdefault("business_name", "SiteForge")
            context.setdefault("banner_image", None)
            context.setdefault("hero_image", None)
            context.setdefault("slider_slides", None)
            context.setdefault("logo", None)
            context.setdefault("hero_title", "Welcome")
            context.setdefault("hero_subtitle", "Your tagline or short description goes here.")
            context.setdefault("footer_intro", "")
            context.setdefault("address_text", "")
            context.setdefault("instagram_url", "")
            context.setdefault("facebook_url", "")
            context.setdefault("youtube_url", "")
            context.setdefault("main_product", None)
            context.setdefault("categories", [])
            context.setdefault("current_category_id", None)
            context.setdefault("map_embed_url", None)
            context.setdefault("spotlight_categories", [])
            context.setdefault("legal_pages_footer", [])
            context.setdefault("announcement_enabled", False)
            context.setdefault("announcement_text", "")
            context.setdefault("announcement_cta_label", "")
            context.setdefault("announcement_cta_url", "")
            context.setdefault("announcement_bg_color", "#0d6efd")
            context.setdefault("announcement_text_color", "#ffffff")
            context.setdefault("popup_enabled", False)
            context.setdefault("popup_title", "")
            context.setdefault("popup_message", "")
            context.setdefault("popup_image_url", "")
            context.setdefault("popup_cta_label", "")
            context.setdefault("popup_cta_url", "")
            context.setdefault("popup_show_rule", "session")
            context.setdefault("popup_seen_key", "default")
            context.setdefault("font_body_key", "inter")
            context.setdefault("font_heading_key", "poppins")
            context.setdefault("font_body_css", FONT_META["inter"]["css"])
            context.setdefault("font_heading_css", FONT_META["poppins"]["css"])
            context.setdefault(
                "font_google_families",
                "|".join(sorted({FONT_META["inter"]["google"], FONT_META["poppins"]["google"]})),
            )
            _empty = Paginator([], HOME_PRODUCTS_PER_PAGE)
            context["products"] = _empty.page(1)
            context["home_products_total_count"] = 0

        if q in ("default", "minimal", "clarity", "aurora", "midnight", "blackred", "emeraldgold"):
            add_seo_context(
                self.request,
                context,
                title=f"{context.get('hero_title', 'Welcome')} — SiteForge",
                description=context.get("hero_subtitle", ""),
                image_url=None,
            )
        elif getattr(self.request, "client", None):
            c = self.request.client
            hero = context.get("hero_title") or "Welcome"
            biz = context.get("business_name") or "SiteForge"
            sub = context.get("hero_subtitle") or ""
            title = (getattr(c, "seo_title", "") or "").strip() or f"{hero} — {biz}"
            desc = (getattr(c, "seo_description", "") or "").strip() or sub or f"Explore products and contact {biz}."
            img = client_site_og_image_url(c, context)
            add_seo_context(
                self.request,
                context,
                title=title,
                description=desc,
                image_url=img,
            )
            context["seo_keywords"] = getattr(c, "seo_keywords", "") or ""
            context["seo_author"] = (getattr(c, "seo_author", "") or "").strip() or biz
        else:
            add_seo_context(
                self.request,
                context,
                title=f"{context.get('hero_title', 'Welcome')} — SiteForge",
                description=context.get("hero_subtitle", ""),
                image_url=context.get("logo") or context.get("banner_image"),
            )
        return context


class ContactSubmitView(FormView):
    """Contact form POST. Saves to ContactSubmission; returns JSON for AJAX (no reload)."""
    form_class = ContactForm
    template_name = "public/home.html"
    success_url = reverse_lazy("home")
    http_method_names = ["post"]

    def get_context_data(self, **kwargs):
        """Merge home page context so non-AJAX validation errors render the full page."""
        context = super().get_context_data(**kwargs)
        index_view = IndexView()
        index_view.setup(self.request, *self.args, **self.kwargs)
        for key, value in index_view.get_context_data().items():
            context.setdefault(key, value)
        return context

    def _is_ajax(self):
        return self.request.headers.get("X-Requested-With") == "XMLHttpRequest"

    def form_valid(self, form):
        from apps.leads.models import ContactSubmission

        client = getattr(self.request, "client", None)
        ContactSubmission.objects.create(
            client=client,
            name=form.cleaned_data["name"],
            email=form.cleaned_data["email"],
            phone=(form.cleaned_data.get("phone") or "")[:50],
            message=form.cleaned_data["message"],
        )
        if self._is_ajax():
            return JsonResponse({"success": True, "message": "Thank you! We'll get back to you soon."})
        return super().form_valid(form)

    def form_invalid(self, form):
        if self._is_ajax():
            return JsonResponse(
                {"success": False, "errors": {k: list(v) for k, v in form.errors.items()}},
                status=400,
            )
        return super().form_invalid(form)


class OptionalPhoneSubmitView(View):
    """POST-only: save optional phone from public modal (tenant-scoped)."""

    http_method_names = ["post"]

    def post(self, request):
        client = getattr(request, "client", None)
        if not client:
            return JsonResponse({"success": False, "message": "Not available."}, status=404)

        if request.headers.get("X-Requested-With") != "XMLHttpRequest":
            return JsonResponse({"success": False, "message": "Invalid request."}, status=400)

        form = OptionalPhoneForm(request.POST)
        if not form.is_valid():
            return JsonResponse(
                {"success": False, "errors": {k: list(v) for k, v in form.errors.items()}},
                status=400,
            )

        from apps.leads.models import OptionalPhoneCapture

        OptionalPhoneCapture.objects.create(
            client=client,
            phone=form.cleaned_data["phone"],
        )
        return JsonResponse(
            {
                "success": True,
                "message": "Thank you — we'll reach out when it matters.",
            }
        )


class ProductSearchSuggestView(View):
    """JSON suggestions for navbar product search (current tenant only)."""

    http_method_names = ["get"]

    def get(self, request):
        client = getattr(request, "client", None)
        if not client:
            return JsonResponse({"results": []})
        q = (request.GET.get("q") or "").strip()
        if len(q) < 2:
            return JsonResponse({"results": []})
        from django.db.models import Q

        from apps.catalog.models import Product

        qs = (
            Product.objects.filter(client=client, is_active=True)
            .filter(Q(name__icontains=q) | Q(description__icontains=q))
            .select_related("category")
            .order_by("order", "name")[:12]
        )
        results = []
        for p in qs:
            results.append(
                {
                    "id": p.pk,
                    "name": p.name,
                    "url": reverse("product_detail", kwargs={"pk": p.pk}),
                    "category": p.category.name if p.category_id else "",
                }
            )
        return JsonResponse({"results": results})


class CampaignEventView(View):
    """Track lightweight campaign analytics (impression/click/close) for popup."""

    http_method_names = ["get"]

    def get(self, request):
        client = getattr(request, "client", None)
        if not client:
            return JsonResponse({"ok": False}, status=404)
        action = (request.GET.get("action") or "").strip().lower()
        if action == "impression":
            client.__class__.objects.filter(pk=client.pk).update(popup_impressions=F("popup_impressions") + 1)
            return JsonResponse({"ok": True})
        if action == "click":
            client.__class__.objects.filter(pk=client.pk).update(popup_clicks=F("popup_clicks") + 1)
            return JsonResponse({"ok": True})
        if action == "close":
            client.__class__.objects.filter(pk=client.pk).update(popup_closes=F("popup_closes") + 1)
            return JsonResponse({"ok": True})
        return JsonResponse({"ok": False, "error": "unknown action"}, status=400)


class ProductListView(ListView):
    """Public product list for current client. 404 if no client."""
    template_name = "public/product_list.html"
    context_object_name = "products"
    paginate_by = PRODUCT_LIST_PER_PAGE

    def get_template_names(self):
        if self.request.GET.get("partial") == "1":
            return ["public/product_list_partial.html"]
        return [self.template_name]

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        if self.request.GET.get("partial") == "1":
            page_obj = context.get("page_obj")
            if page_obj is not None:
                response["X-Has-More"] = "1" if page_obj.has_next() else "0"
        return response

    def get_queryset(self):
        from django.db.models import Q
        from apps.catalog.models import Product

        client = getattr(self.request, "client", None)
        if not client:
            raise Http404("No site configured for this domain.")
        qs = (
            Product.objects.filter(client=client, is_active=True)
            .select_related("category")
            .prefetch_related("size_variants")
            .order_by("order", "name")
        )
        cat_id = self.request.GET.get("category")
        if cat_id:
            try:
                qs = qs.filter(category_id=int(cat_id))
            except (ValueError, TypeError):
                pass
        search = (self.request.GET.get("q") or "").strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        qs = _product_queryset_filter_by_price_range(qs, self.request.GET)
        return qs

    def get_context_data(self, **kwargs):
        from apps.catalog.models import Category

        context = super().get_context_data(**kwargs)
        if getattr(self.request, "client", None):
            ctx = _client_context(self.request, include_catalog_data=False)
            for k, v in ctx.items():
                if k != "products":
                    context.setdefault(k, v)
            context.setdefault("categories", Category.objects.filter(client=self.request.client).order_by("order", "name"))
            try:
                context["current_category_id"] = int(self.request.GET.get("category"))
            except (TypeError, ValueError):
                context["current_category_id"] = None
            context["filter_q"] = self.request.GET.get("q", "")
            context["filter_min_price"] = self.request.GET.get("min_price", "")
            context["filter_max_price"] = self.request.GET.get("max_price", "")
            fa = 0
            if (context.get("filter_q") or "").strip():
                fa += 1
            if context.get("current_category_id"):
                fa += 1
            if context.get("filter_min_price"):
                fa += 1
            if context.get("filter_max_price"):
                fa += 1
            context["filter_active_count"] = fa
            # Category / price / chips only (excludes text search) — mobile drawer badge
            fd = 0
            if context.get("current_category_id"):
                fd += 1
            if context.get("filter_min_price"):
                fd += 1
            if context.get("filter_max_price"):
                fd += 1
            context["filter_drawer_active_count"] = fd
            c = self.request.client
            biz = context.get("business_name") or "SiteForge"
            desc = (getattr(c, "seo_description", "") or "").strip() or f"Browse products from {biz}."
            img = client_site_og_image_url(c, context)
            add_seo_context(
                self.request,
                context,
                title=f"Products — {biz}",
                description=desc,
                image_url=img,
            )
            context["seo_keywords"] = getattr(c, "seo_keywords", "") or ""
            context["seo_author"] = (getattr(c, "seo_author", "") or "").strip() or biz
        return context


class ProductDetailView(DetailView):
    """Public product detail. 404 if no client or product not found for client."""
    template_name = "public/product_detail.html"
    context_object_name = "product"

    def get_queryset(self):
        from apps.catalog.models import Product

        client = getattr(self.request, "client", None)
        if not client:
            return Product.objects.none()
        return (
            Product.objects.filter(client=client, is_active=True)
            .select_related("category")
            .prefetch_related("extra_images", "size_variants")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if getattr(self.request, "client", None):
            ctx = _client_context(self.request, include_catalog_data=False)
            for k, v in ctx.items():
                if k != "products":
                    context.setdefault(k, v)
        product = context.get("product")
        if product:
            gallery_urls = []
            if product.image:
                gallery_urls.append(product.image.url)
            for ei in product.extra_images.all():
                u = ei.image.url
                if u not in gallery_urls:
                    gallery_urls.append(u)
            if not gallery_urls:
                gallery_urls = [static("img/no-image.svg")]
            context["product_gallery_urls"] = gallery_urls
            context["whatsapp_message"] = _whatsapp_product_inquiry_message(self.request, product)
            size_variants = list(product.size_variants.all())
            context["size_variants"] = size_variants
            context["selected_size_default"] = size_variants[0] if size_variants else None
            biz = context.get("business_name") or "SiteForge"
            c = getattr(self.request, "client", None)
            title = (getattr(product, "seo_title", "") or "").strip() or f"{product.name} — {biz}"
            desc = (getattr(product, "seo_description", "") or "").strip() or product.description or product.name
            img = product_og_image_url(product, c, context)
            add_seo_context(
                self.request,
                context,
                title=title,
                description=desc,
                image_url=img,
            )
            context["seo_keywords"] = (getattr(product, "seo_keywords", "") or "").strip() or (getattr(c, "seo_keywords", "") or "")
            context["seo_author"] = (getattr(c, "seo_author", "") or "").strip() or biz

            product_url = self.request.build_absolute_uri(reverse("product_detail", kwargs={"pk": product.pk}))
            schema_image = absolute_media_url(self.request, img or (gallery_urls[0] if gallery_urls else ""))
            seller_schema = {"@type": "Organization", "name": biz}
            price_valid_until = (timezone.now().date() + timedelta(days=30)).isoformat()
            if size_variants:
                offers = []
                low_price = None
                high_price = None
                for sv in size_variants:
                    price_val = float(sv.price)
                    low_price = price_val if low_price is None else min(low_price, price_val)
                    high_price = price_val if high_price is None else max(high_price, price_val)
                    offers.append(
                        {
                            "@type": "Offer",
                            "priceCurrency": "INR",
                            "price": f"{sv.price:.2f}",
                            "availability": "https://schema.org/InStock"
                            if int(sv.stock_qty or 0) > 0
                            else "https://schema.org/OutOfStock",
                            "url": product_url,
                            "sku": f"{product.pk}-{sv.size_label}",
                            "name": f"{product.name} - {sv.size_label}",
                            "seller": seller_schema,
                            "priceValidUntil": price_valid_until,
                        }
                    )
                schema_payload = {
                    "@context": "https://schema.org",
                    "@type": "Product",
                    "name": product.name,
                    "description": plain_text_excerpt(product.description or "", 500),
                    "image": [schema_image] if schema_image else [],
                    "url": product_url,
                    "brand": {"@type": "Brand", "name": biz},
                    "offers": offers,
                    "aggregateOffer": {
                        "@type": "AggregateOffer",
                        "priceCurrency": "INR",
                        "lowPrice": f"{low_price:.2f}",
                        "highPrice": f"{high_price:.2f}",
                        "offerCount": len(offers),
                    },
                }
            else:
                schema_payload = {
                    "@context": "https://schema.org",
                    "@type": "Product",
                    "name": product.name,
                    "description": plain_text_excerpt(product.description or "", 500),
                    "image": [schema_image] if schema_image else [],
                    "url": product_url,
                    "brand": {"@type": "Brand", "name": biz},
                    "offers": {
                        "@type": "Offer",
                        "priceCurrency": "INR",
                        "price": f"{product.price:.2f}",
                        "availability": "https://schema.org/InStock",
                        "url": product_url,
                        "seller": seller_schema,
                        "priceValidUntil": price_valid_until,
                    },
                }
            context["seo_product_schema_json"] = json.dumps(schema_payload, ensure_ascii=False)
            from apps.catalog.models import Product

            if product.category_id:
                context["related_products"] = list(
                    Product.objects.filter(
                        client=product.client,
                        category_id=product.category_id,
                        is_active=True,
                    )
                    .exclude(pk=product.pk)
                    .select_related("category")
                    .prefetch_related("size_variants")
                    .order_by("order", "name")[:10]
                )
            else:
                context["related_products"] = []
        return context


class LegalPageDetailView(TemplateView):
    template_name = "public/legal_page.html"

    def get_context_data(self, **kwargs):
        from apps.tenants.models import LegalPage

        context = super().get_context_data(**kwargs)
        client = getattr(self.request, "client", None)
        if not client:
            raise Http404("No site configured for this domain.")
        page = get_object_or_404(
            LegalPage.objects.filter(client=client, is_active=True),
            slug=self.kwargs["slug"],
        )
        base_ctx = _client_context(self.request, include_catalog_data=False)
        for k, v in base_ctx.items():
            if k not in {"products", "main_product"}:
                context.setdefault(k, v)
        context["legal_page"] = page
        context["seo_keywords"] = (getattr(client, "seo_keywords", "") or "").strip()
        context["seo_author"] = (getattr(client, "seo_author", "") or "").strip() or context.get("business_name") or "SiteForge"
        add_seo_context(
            self.request,
            context,
            title=f"{page.title} — {context.get('business_name') or 'SiteForge'}",
            description=plain_text_excerpt(page.content or page.title, 300),
            image_url=client_site_og_image_url(client, context),
        )
        return context


def tenant_public_sitemap(request):
    """XML sitemap for the tenant resolved from the Host header (not for admin/dashboard hosts)."""
    client = getattr(request, "client", None)
    if not client:
        raise Http404("No site is configured for this host.")
    return sitemap_index_view(request, {"public": TenantPublicSitemap(client)})


def handler404(request, exception):
    """Friendly page not found (used when DEBUG is False, and for some debug 404s)."""
    ctx = {}
    client = getattr(request, "client", None)
    if client:
        ctx["business_name"] = client.business_name
    return render(request, "errors/404.html", ctx, status=404)


def handler500(request):
    """Friendly server error; keep logic minimal (DB may be unavailable)."""
    return render(request, "errors/500.html", status=500)


def handler403(request, exception):
    ctx = {}
    client = getattr(request, "client", None)
    if client:
        ctx["business_name"] = client.business_name
    return render(request, "errors/403.html", ctx, status=403)
