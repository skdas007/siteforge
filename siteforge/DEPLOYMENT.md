# SiteForge deployment guide (no Docker)

This guide covers deploying the Django project on a Linux server using **Gunicorn**, **systemd**, and **Nginx**.

**Database**: The app uses **SQLite** by default. The file `db.sqlite3` is created in the project root (same directory as `manage.py`). No extra database server is required.

---

## 1. Server requirements

- **OS**: Ubuntu 22.04 LTS or similar (Debian, CentOS work too)
- **User**: A dedicated app user (e.g. `siteforge`) is recommended
- **Python**: 3.10 or 3.11

---

## 2. Install system packages

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nginx
```

No database server is needed when using SQLite (`db.sqlite3`).

---

## 3. Deploy the application

### 3.1 Create app user (optional)

```bash
sudo useradd -m -s /bin/bash siteforge
sudo su - siteforge
```

### 3.2 Clone or upload the project

Example with Git (from your machine you can push; on server):

```bash
cd /home/siteforge
git clone <your-repo-url> app
cd app/siteforge
```

Or upload the project (e.g. `my_project/siteforge`) to something like `/home/siteforge/app/siteforge` so that `manage.py` is at `/home/siteforge/app/siteforge/manage.py`.

### 3.3 Create virtual environment and install dependencies

```bash
cd /home/siteforge/app/siteforge   # or your actual path
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements/production.txt
```

---

## 4. Environment variables

Create a `.env` file in the **project root** (same directory as `manage.py`):

```bash
nano .env
```

Use these variables for **production** (adjust values):

```env
# Required
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=your-long-random-secret-key-here
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,203.0.113.10

# Optional (defaults shown)
DEBUG=False
# SQLite: leave DATABASE_PATH unset to use db.sqlite3 in project root
STATIC_ROOT=/home/siteforge/app/siteforge/staticfiles
MEDIA_ROOT=/home/siteforge/app/siteforge/media

# If using S3 for uploads (optional)
# AWS_STORAGE_BUCKET_NAME=your-bucket
# AWS_ACCESS_KEY_ID=...
# AWS_SECRET_ACCESS_KEY=...
# AWS_S3_REGION_NAME=us-east-1
```

Generate a secret key (run once, paste into `.env`):

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

Secure the file:

```bash
chmod 600 .env
```

---

## 5. Database and static files

Run with the virtualenv activated and `DJANGO_SETTINGS_MODULE` set (either in `.env` or export below):

```bash
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.production
# If .env is not loaded by your process, also export:
# set -a && source .env && set +a

python manage.py migrate
python manage.py collectstatic --noinput
```

Create a superuser if needed:

```bash
python manage.py createsuperuser
```

---

## 6. Run Gunicorn (test)

From the project directory (where `manage.py` is):

```bash
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.production
gunicorn config.wsgi:application --bind 127.0.0.1:8000
```

Visit `http://your-server-ip:8000` only if you temporarily allow it (e.g. for testing). Normally you’ll put Nginx in front (next step).

---

## 7. Systemd service (Gunicorn as a daemon)

Create a unit file (adjust paths and user):

```bash
sudo nano /etc/systemd/system/siteforge.service
```

```ini
[Unit]
Description=SiteForge Gunicorn
After=network.target

[Service]
User=siteforge
Group=siteforge
WorkingDirectory=/home/siteforge/app/siteforge
Environment="PATH=/home/siteforge/app/siteforge/venv/bin"
EnvironmentFile=/home/siteforge/app/siteforge/.env
ExecStart=/home/siteforge/app/siteforge/venv/bin/gunicorn \
    --workers 3 \
    --bind 127.0.0.1:8000 \
    --access-logfile - \
    --error-logfile - \
    config.wsgi:application

Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

If `EnvironmentFile` doesn’t load `.env` on your system, replace it with explicit variables:

```ini
Environment=DJANGO_SETTINGS_MODULE=config.settings.production
Environment=SECRET_KEY=your-secret-key
Environment=ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable siteforge
sudo systemctl start siteforge
sudo systemctl status siteforge
```

---

## 8. Nginx (reverse proxy and static files)

Create a site config (replace `yourdomain.com` and paths):

```bash
sudo nano /etc/nginx/sites-available/siteforge
```

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    client_max_body_size 20M;

    # Static files (Django collectstatic)
    location /static/ {
        alias /home/siteforge/app/siteforge/staticfiles/;
    }

    # Media files (if not using S3)
    location /media/ {
        alias /home/siteforge/app/siteforge/media/;
    }

    # Proxy to Gunicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site and reload Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/siteforge /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 9. SSL with Let’s Encrypt (recommended)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

Certbot will adjust your Nginx config for HTTPS. Renewal is automatic.

---

## 10. Checklist after deployment

| Task | Command / note |
|------|----------------|
| Migrations | `python manage.py migrate` |
| Static files | `python manage.py collectstatic --noinput` |
| Superuser | `python manage.py createsuperuser` |
| Gunicorn | `systemctl status siteforge` |
| Nginx | `systemctl status nginx` |
| Logs | `journalctl -u siteforge -f` |

---

## 11. Updates (after code changes)

```bash
cd /home/siteforge/app/siteforge
source venv/bin/activate
git pull   # or upload new code
pip install -r requirements/production.txt
export DJANGO_SETTINGS_MODULE=config.settings.production
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart siteforge
```

---

## 12. Troubleshooting

- **502 Bad Gateway**: Gunicorn not running or not listening on `127.0.0.1:8000`. Check `systemctl status siteforge` and `journalctl -u siteforge -n 50`.
- **Static files 404**: Run `collectstatic` and ensure `location /static/` alias path matches `STATIC_ROOT`.
- **ModuleNotFoundError / dotenv**: Ensure `python-dotenv` is installed (`pip install -r requirements/production.txt`) and `.env` path is correct.
- **ALLOWED_HOSTS**: Add your domain and server IP to `ALLOWED_HOSTS` in `.env`.

If you use **PostgreSQL** later, set `DATABASE_URL` (or equivalent) in `.env` and switch `config.settings.base` to use it; the same deployment steps apply.
