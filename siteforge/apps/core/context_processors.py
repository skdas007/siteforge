"""Template context available on all requests."""


def favicon_url(request):
    """
    Public site uses request.client (middleware); dashboard uses request.user.client
    when the tenant middleware did not attach client.
    """
    url = None
    client = getattr(request, "client", None)
    if not client and getattr(request, "user", None) and request.user.is_authenticated:
        client = getattr(request.user, "client", None)
    if client and getattr(client, "favicon", None):
        try:
            url = client.favicon.url
        except ValueError:
            url = None
    return {"favicon_url": url}
