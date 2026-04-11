"""Helpers for SEO and Open Graph / Twitter Card (link preview) metadata."""

from django.utils.html import strip_tags


def absolute_media_url(request, url) -> str:
    """
    Return an absolute URL suitable for og:image / twitter:image.
    Handles already-absolute URLs (e.g. S3) and site-relative paths (/media/...).
    """
    if not url:
        return ""
    u = str(url).strip()
    if not u:
        return ""
    if u.startswith("//"):
        return f"{request.scheme}:{u}"
    if u.startswith(("http://", "https://")):
        return u
    if u.startswith("/"):
        return request.build_absolute_uri(u)
    return request.build_absolute_uri(f"/{u.lstrip('/')}")


def plain_text_excerpt(html_or_text: str, max_len: int = 160) -> str:
    """Strip tags and collapse whitespace for meta descriptions."""
    t = strip_tags(html_or_text or "").strip()
    if not t:
        return ""
    t = " ".join(t.split())
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "…"


def client_site_og_image_url(client, context: dict):
    """
    og:image for home, product list, and other non-product pages:
    client's uploaded SEO image, else logo, then banner, then hero/welcome image.
    """
    if client is not None and getattr(client, "seo_image", None) and client.seo_image:
        return client.seo_image.url
    return context.get("logo") or context.get("banner_image") or context.get("hero_image")


def product_og_image_url(product, client, context: dict):
    """
    og:image for a product detail page:
    product SEO image → primary product image → first gallery image →
    client's site SEO image → logo → banner → hero.
    """
    if getattr(product, "seo_image", None) and product.seo_image:
        return product.seo_image.url
    if product.image:
        return product.image.url
    first_extra = product.extra_images.first()
    if first_extra:
        return first_extra.image.url
    if client is not None and getattr(client, "seo_image", None) and client.seo_image:
        return client.seo_image.url
    return context.get("logo") or context.get("banner_image") or context.get("hero_image")


def add_seo_context(request, context: dict, *, title: str, description: str = "", image_url=None, og_type: str = "website"):
    """
    Set template variables used by templates/includes/seo_meta.html.
    image_url: FileField.url or None (may be relative or absolute).
    Canonical and og:url are built in the template from the request.
    """
    context["seo_title"] = (title or "").strip() or "SiteForge"
    context["seo_description"] = plain_text_excerpt(description, 300) or plain_text_excerpt(title, 300)
    context["seo_image_url"] = image_url
    context["seo_type"] = og_type
