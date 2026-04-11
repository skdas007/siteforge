from django import template

from apps.core.seo_utils import absolute_media_url

register = template.Library()


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
