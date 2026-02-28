"""
Django base settings for SiteForge.
Load from environment where possible; see env.example.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env from project root (siteforge/.env) if present
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_file)

# Security: override in production via env
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-change-me-in-production")

DEBUG = os.environ.get("DEBUG", "True").lower() in ("1", "true", "yes")

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "storages",
    "apps.core",
    "apps.tenants",
    "apps.themes",
    "apps.catalog",
    "apps.leads",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "apps.core.middleware.TenantResolutionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database: SQLite for now; use DATABASE_URL for PostgreSQL later
DATABASE_PATH = os.environ.get("DATABASE_PATH", str(BASE_DIR / "db.sqlite3"))
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATABASE_PATH,
    }
}

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "home"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []
STATIC_ROOT = os.environ.get("STATIC_ROOT", str(BASE_DIR / "staticfiles"))

# Media and static: use S3 when AWS_STORAGE_BUCKET_NAME is set
AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME", "").strip()
if AWS_STORAGE_BUCKET_NAME:
    _aws_access = os.environ.get("AWS_ACCESS_KEY_ID") or os.environ.get("AWS_ACCESS_KEY", "")
    _aws_secret = os.environ.get("AWS_SECRET_ACCESS_KEY") or os.environ.get("AWS_SECREAT_KEY", "")
    _aws_region = os.environ.get("AWS_S3_REGION_NAME", "us-east-1")
    _aws_domain = os.environ.get("AWS_S3_CUSTOM_DOMAIN", "").strip() or None
    _s3_base = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{_aws_region}.amazonaws.com/"
    if _aws_domain:
        _s3_base = f"https://{_aws_domain}/"
    _s3_opts = {
        "bucket_name": AWS_STORAGE_BUCKET_NAME,
        "access_key": _aws_access,
        "secret_key": _aws_secret,
        "region_name": _aws_region,
        "object_parameters": {"CacheControl": "max-age=86400"},
        "default_acl": None,
        "file_overwrite": False,
        "querystring_auth": True,
        "custom_domain": _aws_domain,
    }
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {**_s3_opts, "location": "media"},
        },
        "staticfiles": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {**_s3_opts, "location": "static"},
        },
    }
    MEDIA_URL = _s3_base + "media/"
    STATIC_URL = _s3_base + "static/"
    MEDIA_ROOT = ""
else:
    MEDIA_URL = "media/"
    MEDIA_ROOT = os.environ.get("MEDIA_ROOT", str(BASE_DIR / "media"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
