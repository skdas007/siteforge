"""Per-tenant XML sitemap for public storefront URLs."""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class TenantPublicSitemap(Sitemap):
    """
    URLs for the current tenant only (client is set on the sitemap instance).
    Served at /sitemap.xml after TenantResolutionMiddleware sets request.client.
    """

    def __init__(self, client):
        self.client = client
        super().__init__()

    def items(self):
        from apps.catalog.models import Product

        entries = [
            ("home", None),
            ("product_list", None),
            ("contact", None),
        ]
        qs = (
            Product.objects.filter(client=self.client, is_active=True)
            .only("pk", "updated_at")
            .order_by("order", "name", "pk")
        )
        for product in qs:
            entries.append(("product", product))
        return entries

    def location(self, item):
        kind, obj = item
        if kind == "home":
            return reverse("home")
        if kind == "product_list":
            return reverse("product_list")
        if kind == "contact":
            return reverse("contact_submit")
        if kind == "product":
            return reverse("product_detail", kwargs={"pk": obj.pk})
        return "/"

    def lastmod(self, item):
        kind, obj = item
        if kind == "product" and obj is not None:
            return obj.updated_at
        return None

    def priority(self, item):
        kind, _ = item
        if kind == "home":
            return 1.0
        if kind == "product_list":
            return 0.9
        if kind == "product":
            return 0.8
        return 0.5

    def changefreq(self, item):
        kind, _ = item
        if kind == "product":
            return "weekly"
        if kind == "home":
            return "weekly"
        return "monthly"
