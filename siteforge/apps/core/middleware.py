"""
Multi-tenant resolution: set request.client from request host.
Skip for admin, dashboard, static, media so they work without a tenant domain.
"""
from django.conf import settings
from django.http import HttpResponseNotFound
from django.utils.deprecation import MiddlewareMixin


def _normalize_domain(host):
    """Lowercase and strip port (e.g. 'Host:8080' -> 'host')."""
    if not host:
        return ""
    return host.lower().split(":")[0].strip()


def _should_skip_tenant_resolution(path):
    """Paths that do not require a tenant (admin, dashboard, static, media)."""
    skip_prefixes = ("/admin/", "/dashboard/", "/static/", "/media/", "/favicon.ico")
    path = (path or "").strip("/")
    path = "/" + path + "/" if path else "/"
    return any(path.startswith(p) or path == p.rstrip("/") for p in skip_prefixes)


class TenantResolutionMiddleware(MiddlewareMixin):
    """
    Resolve client from request host and set request.client.
    Return 404 for unknown or inactive domains when tenant is required.
    In DEBUG, unknown domains get request.client = None so localhost works without a Client.
    """

    def process_request(self, request):
        if _should_skip_tenant_resolution(request.path):
            request.client = None
            return None

        host = request.META.get("HTTP_X_FORWARDED_HOST") or request.get_host()
        domain = _normalize_domain(host)

        if not domain:
            request.client = None
            return None

        from apps.tenants.models import Client

        try:
            client = Client.objects.select_related("theme").get(domain=domain, is_active=True)
        except Client.DoesNotExist:
            if settings.DEBUG:
                request.client = None
                return None
            return HttpResponseNotFound("<h1>Site not found</h1><p>No site is configured for this domain.</p>")

        request.client = client
        return None
