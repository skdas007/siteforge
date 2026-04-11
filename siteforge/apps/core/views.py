from django.contrib.sitemaps.views import sitemap as sitemap_index_view
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView

from apps.core.seo_utils import add_seo_context, client_site_og_image_url, product_og_image_url
from apps.core.sitemaps import TenantPublicSitemap

HOME_PRODUCTS_PER_PAGE = 6
PRODUCT_LIST_PER_PAGE = 9

from .forms import ContactForm


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
    price = getattr(product, "price", None)
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


def _client_context(request):
    """Build template context from request.client when set (multi-tenant)."""
    from apps.catalog.models import Product
    from apps.tenants.models import CarouselSlide

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
    products = Product.objects.filter(client=client, is_active=True).order_by("order", "name")
    main_product = products.filter(is_main=True).first() or products.first()
    return {
        "theme_slug": client.theme_slug,
        "business_name": client.business_name,
        "banner_image": client.banner_image.url if client.banner_image else None,
        "hero_image": client.hero_image.url if client.hero_image else None,
        "logo": client.logo.url if client.logo else None,
        "hero_title": client.hero_title or "Welcome",
        "hero_subtitle": client.hero_subtitle or "Your tagline or short description goes here.",
        "contact_email": client.contact_email,
        "whatsapp_number": (getattr(client, "whatsapp_number", "") or "").strip(),
        "whatsapp_digits": "".join(c for c in (getattr(client, "whatsapp_number", "") or "") if c.isdigit()),
        "map_embed_url": getattr(client, "map_embed_url", None),
        "slider_slides": slider_slides,
        "main_product": main_product,
        "products": products,
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
        if q in ("default", "minimal", "clarity"):
            context["theme_slug"] = q
            _empty = Paginator([], HOME_PRODUCTS_PER_PAGE)
            context["products"] = _empty.page(1)
            context["home_products_total_count"] = 0
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
            context.setdefault("main_product", None)
            context.setdefault("categories", [])
            context.setdefault("current_category_id", None)
            context.setdefault("map_embed_url", None)
            _empty = Paginator([], HOME_PRODUCTS_PER_PAGE)
            context["products"] = _empty.page(1)
            context["home_products_total_count"] = 0

        if q in ("default", "minimal", "clarity"):
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
        from apps.catalog.models import Category, Product

        client = getattr(self.request, "client", None)
        if not client:
            raise Http404("No site configured for this domain.")
        qs = Product.objects.filter(client=client, is_active=True).select_related("category").order_by("order", "name")
        cat_id = self.request.GET.get("category")
        if cat_id:
            try:
                Category.objects.get(pk=int(cat_id), client=client)
                qs = qs.filter(category_id=int(cat_id))
            except (ValueError, TypeError, Category.DoesNotExist):
                pass
        search = (self.request.GET.get("q") or "").strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        try:
            min_p = self.request.GET.get("min_price")
            if min_p is not None and min_p != "":
                qs = qs.filter(price__gte=float(min_p))
        except (ValueError, TypeError):
            pass
        try:
            max_p = self.request.GET.get("max_price")
            if max_p is not None and max_p != "":
                qs = qs.filter(price__lte=float(max_p))
        except (ValueError, TypeError):
            pass
        return qs

    def get_context_data(self, **kwargs):
        from apps.catalog.models import Category

        context = super().get_context_data(**kwargs)
        if getattr(self.request, "client", None):
            ctx = _client_context(self.request)
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
            .prefetch_related("extra_images")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if getattr(self.request, "client", None):
            ctx = _client_context(self.request)
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
                    .order_by("order", "name")[:10]
                )
            else:
                context["related_products"] = []
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
