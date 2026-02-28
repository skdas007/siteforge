"""
Verify S3 media storage: list objects in the bucket and optionally test upload.
Usage: python manage.py verify_s3 [--upload-test]
"""
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Verify S3 bucket connectivity and list media files (tenants/)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--upload-test",
            action="store_true",
            help="Upload a small test file and then list to confirm.",
        )

    def handle(self, *args, **options):
        bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", None) or ""
        if not bucket:
            self.stdout.write(
                self.style.WARNING("AWS_STORAGE_BUCKET_NAME is not set. Media is stored locally (MEDIA_ROOT).")
            )
            return

        storage = None
        try:
            from django.core.files.storage import default_storage

            storage = default_storage
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Could not get default storage: {e}"))
            return

        backend = getattr(storage, "backend", None) or type(storage).__name__
        self.stdout.write(f"Default storage: {backend}")
        self.stdout.write(f"Bucket: {bucket}")

        # List existing objects (django-storages may not have listdir; use boto3 if needed)
        try:
            if hasattr(storage, "bucket"):
                s3_bucket = storage.bucket
                prefix = "tenants/"
                self.stdout.write(f"\nListing objects under '{prefix}':")
                count = 0
                for obj in s3_bucket.objects.filter(Prefix=prefix):
                    count += 1
                    self.stdout.write(f"  {obj.key} ({obj.size} bytes)")
                if count == 0:
                    self.stdout.write(self.style.WARNING(f"  No objects found under '{prefix}'"))
                else:
                    self.stdout.write(self.style.SUCCESS(f"  Total: {count} object(s)"))
            else:
                # Fallback: try listdir if no bucket attr
                try:
                    dirs, files = storage.listdir("tenants/")
                    self.stdout.write("\nListing tenants/: dirs=%s, files=%s" % (dirs, files))
                except Exception as e2:
                    self.stdout.write(self.style.WARNING("Could not list bucket (listdir): %s" % e2))
        except Exception as e:
            self.stdout.write(self.style.ERROR("Could not list S3 bucket: %s" % e))

        if options.get("upload_test"):
            test_key = "tenants/verify_s3_test.txt"
            try:
                storage.save(test_key, ContentFile(b"SiteForge S3 verify test"))
                self.stdout.write(self.style.SUCCESS("\nUploaded test file: %s" % test_key))
                if hasattr(storage, "bucket"):
                    obj = storage.bucket.Object(test_key)
                    obj.load()
                    self.stdout.write("  Confirmed in bucket (size=%s)" % obj.content_length)
                storage.delete(test_key)
                self.stdout.write("  Deleted test file.")
            except Exception as e:
                self.stdout.write(self.style.ERROR("Upload test failed: %s" % e))
