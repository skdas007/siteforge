"""
Create a demo User + Client for local testing on localhost.
Usage: python manage.py create_demo_client
Then open http://localhost:8000/, log in as the demo user, and use the dashboard.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.themes.models import Theme
from apps.tenants.models import Client


class Command(BaseCommand):
    help = "Create a demo client for localhost so you can test superadmin → client → upload content."

    def add_arguments(self, parser):
        parser.add_argument(
            "--domain",
            default="localhost",
            help="Domain for the client (default: localhost). Use 127.0.0.1 if you open that in the browser.",
        )
        parser.add_argument(
            "--username",
            default="client",
            help="Username for the client login (default: client).",
        )
        parser.add_argument(
            "--password",
            default="client123",
            help="Password for the client user (default: client123).",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        domain = options["domain"].strip().lower()
        username = options["username"]
        password = options["password"]

        if Client.objects.filter(domain=domain).exists():
            self.stdout.write(self.style.WARNING(f"A client for domain '{domain}' already exists. Skipping."))
            client = Client.objects.get(domain=domain)
            if client.user:
                self.stdout.write(f"  Login: http://localhost:8000/accounts/login/ → user: {client.user.username}")
            return

        theme = Theme.objects.filter(is_active=True).first()
        if not theme:
            theme = Theme.objects.create(name="Default", slug="default", is_active=True)
            self.stdout.write(f"Created Theme: {theme.slug}")

        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": f"{username}@example.com", "is_staff": False, "is_active": True},
        )
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created user: {username}"))
        else:
            self.stdout.write(f"Using existing user: {username} (password unchanged)")

        client = Client.objects.create(
            user=user,
            business_name="Demo Client",
            slug="demo-client",
            domain=domain,
            theme=theme,
            hero_title="Welcome to our site",
            hero_subtitle="Edit this in the dashboard.",
            is_active=True,
        )
        self.stdout.write(self.style.SUCCESS(f"Created client: {client.business_name} ({domain})"))

        self.stdout.write("")
        self.stdout.write("Next steps:")
        self.stdout.write(f"  1. Open http://localhost:8000/  (use http://{domain}:8000/ if different)")
        self.stdout.write(f"  2. Log in: http://localhost:8000/accounts/login/  → {username} / {password}")
        self.stdout.write("  3. Go to Dashboard → Settings and upload/edit content (hero, logo, banner).")
        self.stdout.write("  4. Visit the home page again to see your content.")
