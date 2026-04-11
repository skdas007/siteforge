"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path

from apps.core.views import (
    ContactSubmitView,
    IndexView,
    ProductDetailView,
    ProductListView,
    ProductSearchSuggestView,
)

urlpatterns = [
    path("", IndexView.as_view(), name="home"),
    path("contact/", ContactSubmitView.as_view(), name="contact_submit"),
    path("api/product-suggest/", ProductSearchSuggestView.as_view(), name="product_search_suggest"),
    path("products/", ProductListView.as_view(), name="product_list"),
    path("products/<int:pk>/", ProductDetailView.as_view(), name="product_detail"),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            extra_context={
                "seo_title": "Log in — Dashboard",
                "seo_description": "Sign in to manage your SiteForge dashboard.",
                "seo_image_url": None,
                "seo_type": "website",
            },
        ),
        name="login",
    ),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("dashboard/", include("apps.tenants.urls", namespace="dashboard")),
    path("admin/", admin.site.urls),
]

# When DEBUG=True, serve static from STATICFILES_DIRS / app static (not only via runserver's handler).
# Helps: django.test.Client, Gunicorn/uWSGI with DEBUG=True, and some local setups.
if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
