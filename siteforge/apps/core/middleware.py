"""
Multi-tenant resolution: set request.client from request host.
Skip for admin, dashboard, static, media so they work without a tenant domain.
"""
from django.conf import settings
from django.http import HttpResponsePermanentRedirect
from django.shortcuts import render
from django.utils.deprecation import MiddlewareMixin


def _normalize_domain(host):
    """Lowercase and strip port (e.g. 'Host:8080' -> 'host')."""
    if not host:
        return ""
    return host.lower().split(":")[0].strip()


def _alternate_domain(domain):
    """
    Return www/non-www variant of a domain.
    - www.example.com -> example.com
    - example.com -> www.example.com
    """
    domain = (domain or "").strip().lower()
    if not domain:
        return ""
    if domain.startswith("www."):
        return domain[4:]
    return f"www.{domain}"


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

        resolved_by_alias = False
        try:
            client = Client.objects.select_related("theme").get(domain=domain, is_active=True)
        except Client.DoesNotExist:
            alt = _alternate_domain(domain)
            try:
                client = Client.objects.select_related("theme").get(domain=alt, is_active=True)
                resolved_by_alias = True
            except Client.DoesNotExist:
                client = None

        if client is None:
            if settings.DEBUG:
                request.client = None
                return None
            return render(
                request,
                "errors/site_not_found.html",
                {"business_name": None},
                status=404,
            )

        # Keep one canonical host: always redirect to Client.domain if request host differs.
        # This removes www/non-www mismatch without requiring CDN redirect rules.
        if resolved_by_alias and domain != client.domain:
            scheme = request.META.get("HTTP_X_FORWARDED_PROTO") or request.scheme or "https"
            full_path = request.get_full_path() or "/"
            target = f"{scheme}://{client.domain}{full_path}"
            return HttpResponsePermanentRedirect(target)

        request.client = client
        return None
