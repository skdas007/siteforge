"""Dashboard mixins: require login and client (user must be linked to a Client)."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404

from .models import Client


class DashboardClientMixin(LoginRequiredMixin):
    """
    Require login and that the user has an associated Client.
    Sets self.client = request.user.client; 404 if user has no client.
    """
    login_url = "login"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        try:
            request.user.client
        except Client.DoesNotExist:
            raise Http404("No client is linked to your account. Contact the administrator.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["client"] = self.request.user.client
        return context
