"""
Development settings for SiteForge.
"""
from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "bobdy", "bobdyinternational", "*"]

# Allow CSRF when using different local hostnames (e.g. localhost vs bobdy)
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://bobdy:8000",
    "http://bobdyinternational:8000"
]

# Store CSRF token in session so it matches the same domain as your login (avoids cookie mismatch)
CSRF_USE_SESSIONS = True
