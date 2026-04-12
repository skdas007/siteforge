from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.DashboardHomeView.as_view(), name="home"),
    path("settings/", views.DashboardSettingsView.as_view(), name="settings"),
    path("settings/carousel-reorder/", views.CarouselReorderView.as_view(), name="carousel_reorder"),
    path("categories/", views.CategoryListView.as_view(), name="category_list"),
    path("categories/add/", views.CategoryCreateView.as_view(), name="category_add"),
    path("categories/<int:pk>/delete/", views.CategoryDeleteView.as_view(), name="category_delete"),
    path("products/", views.ProductListView.as_view(), name="product_list"),
    path("products/reorder/", views.ProductReorderView.as_view(), name="product_reorder"),
    path("products/add/", views.ProductAddView.as_view(), name="product_add"),
    path("products/<int:pk>/edit/", views.ProductEditView.as_view(), name="product_edit"),
    path("products/<int:pk>/delete/", views.ProductDeleteView.as_view(), name="product_delete"),
    path("contacts/", views.ContactSubmissionListView.as_view(), name="contact_list"),
    path("contacts/bulk-delete/", views.ContactSubmissionBulkDeleteView.as_view(), name="contact_bulk_delete"),
    path("contacts/<int:pk>/delete/", views.ContactSubmissionDeleteView.as_view(), name="contact_delete"),
]
