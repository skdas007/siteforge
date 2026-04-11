from django import template

from apps.core.seo_utils import absolute_media_url

register = template.Library()


@register.filter
def og_image_mime(url):
    """Guess image/* type from URL path for og:image:type (helps Facebook/WhatsApp crawlers)."""
    if not url:
        return "image/jpeg"
    path = str(url).split("?")[0].lower()
    if path.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if path.endswith(".png"):
        return "image/png"
    if path.endswith(".webp"):
        return "image/webp"
    if path.endswith(".gif"):
        return "image/gif"
    return "image/jpeg"


@register.simple_tag(takes_context=True)
def canonical_page_url(context):
    """Absolute URL without query string (link rel=canonical)."""
    request = context["request"]
    return request.build_absolute_uri(request.path)


@register.simple_tag(takes_context=True)
def share_page_url(context):
    """Absolute URL including query string (og:url should match the shared link)."""
    request = context["request"]
    return request.build_absolute_uri(request.get_full_path())


@register.simple_tag(takes_context=True)
def absolute_og_image(context, url):
    """Build absolute image URL for og:image from a .url string (relative or S3)."""
    request = context.get("request")
    if not request or not url:
        return ""
    return absolute_media_url(request, url)
