"""
Production settings for SiteForge.
Set SECRET_KEY, ALLOWED_HOSTS, DEBUG=False via environment.
"""
from .base import *  # noqa: F401, F403

DEBUG = False
# ALLOWED_HOSTS and SECRET_KEY must be set in environment
