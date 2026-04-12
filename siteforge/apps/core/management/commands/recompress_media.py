"""
Recompress existing ImageField files in storage (S3 or local) to WebP/AVIF.

Does not run model save(); updates DB path with QuerySet.update().
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.catalog.models import Product, ProductImage
from apps.core.image_compression import recompress_field_file
from apps.tenants.models import Client, CarouselSlide
from apps.themes.models import Theme


class Command(BaseCommand):
    help = "Recompress stored raster images (WebP by default). Skips missing files, animated GIFs, SVG."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing storage or DB.",
        )
        parser.add_argument(
            "--client-id",
            type=int,
            default=None,
            help="Limit products, product extras, and carousel slides to this tenants.Client id.",
        )
        parser.add_argument(
            "--scope",
            choices=["all", "products", "product-extra", "clients", "carousel", "themes"],
            default="all",
            help="Which models to process (default: all).",
        )
        parser.add_argument(
            "--include-webp",
            action="store_true",
            help="Also process files already ending in .webp or .avif.",
        )
        parser.add_argument(
            "--force-bigger",
            action="store_true",
            help="Upload even when output size is not smaller than the original.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        client_id = options["client_id"]
        scope = options["scope"]
        skip_modern = not options["include_webp"]
        skip_if_not_smaller = not options["force_bigger"]

        stats = {
            "ok": 0,
            "dry-run": 0,
            "skip": 0,
            "missing": 0,
            "error": 0,
            "no-op": 0,
        }

        def run_field(instance, field_name: str, max_side: int) -> None:
            r = recompress_field_file(
                instance,
                field_name,
                max_side=max_side,
                dry_run=dry_run,
                skip_if_smaller_or_equal=skip_if_not_smaller,
                skip_modern_formats=skip_modern,
            )
            stats[r] = stats.get(r, 0) + 1
            if r in ("ok", "dry-run"):
                self.stdout.write(f"  {r}: {instance.__class__.__name__} pk={instance.pk} {field_name}")

        if scope in ("all", "products"):
            qs = Product.objects.all().order_by("pk")
            if client_id is not None:
                qs = qs.filter(client_id=client_id)
            for p in qs.iterator():
                if p.image:
                    run_field(p, "image", settings.IMAGE_UPLOAD_MAX_SIDE)
                if p.seo_image:
                    run_field(p, "seo_image", settings.IMAGE_UPLOAD_SEO_MAX_SIDE)

        if scope in ("all", "product-extra"):
            qs = ProductImage.objects.select_related("product").order_by("pk")
            if client_id is not None:
                qs = qs.filter(product__client_id=client_id)
            for row in qs.iterator():
                run_field(row, "image", settings.IMAGE_UPLOAD_MAX_SIDE)

        if scope in ("all", "clients"):
            cqs = Client.objects.all().order_by("pk")
            if client_id is not None:
                cqs = cqs.filter(pk=client_id)
            for c in cqs.iterator():
                if c.banner_image:
                    run_field(c, "banner_image", settings.IMAGE_UPLOAD_BANNER_MAX_SIDE)
                if c.hero_image:
                    run_field(c, "hero_image", settings.IMAGE_UPLOAD_BANNER_MAX_SIDE)
                if c.logo:
                    run_field(c, "logo", settings.IMAGE_UPLOAD_LOGO_MAX_SIDE)
                if c.seo_image:
                    run_field(c, "seo_image", settings.IMAGE_UPLOAD_SEO_MAX_SIDE)

        if scope in ("all", "carousel"):
            qs = CarouselSlide.objects.all().order_by("pk")
            if client_id is not None:
                qs = qs.filter(client_id=client_id)
            for s in qs.iterator():
                if s.image:
                    run_field(s, "image", settings.IMAGE_UPLOAD_BANNER_MAX_SIDE)

        if scope == "themes" and client_id is not None:
            self.stdout.write(self.style.WARNING("--client-id is ignored for themes."))

        if scope == "themes" or (scope == "all" and client_id is None):
            for t in Theme.objects.all().order_by("pk").iterator():
                if t.preview_image:
                    run_field(t, "preview_image", settings.IMAGE_UPLOAD_THEME_PREVIEW_MAX_SIDE)

        self.stdout.write(self.style.SUCCESS(f"Done. Counts: {stats}"))
