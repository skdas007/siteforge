"""
Gunicorn config for SiteForge. Use from project root:
  gunicorn -c deploy/gunicorn.conf.py config.wsgi:application
"""
import os

bind = "127.0.0.1:8000"
workers = 3
worker_class = "sync"
worker_tmp_dir = os.environ.get("TMPDIR", "/tmp")
accesslog = "-"
errorlog = "-"
loglevel = "info"
capture_output = True
