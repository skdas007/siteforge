# SiteForge deployment guide (no Docker)

This guide covers deploying the Django project on a Linux server using **Gunicorn**, **systemd**, and **Nginx**.

**Database**: The app uses **SQLite** by default. The file `db.sqlite3` is created in the project root (same directory as `manage.py`). No extra database server is required.

**Config in repo**: Nginx and Gunicorn configs live in **`deploy/`** so you can version them and copy or link from the project on the server.

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
ALLOWED_HOSTS=bobdyinternational.com,www.bobdyinternational.com,amberonlinestore.com,www.amberonlinestore.com

# Optional (defaults shown)
DEBUG=False
# SQLite: leave DATABASE_PATH unset to use db.sqlite3 in project root
# When using S3 (below), static and media are in the bucket; no STATIC_ROOT/MEDIA_ROOT needed for serving.
# STATIC_ROOT=...
# MEDIA_ROOT=...

# S3: when set, static and media are stored in the bucket (recommended for production)
# AWS_STORAGE_BUCKET_NAME=your-bucket-name
# AWS_ACCESS_KEY_ID=...
# AWS_SECRET_ACCESS_KEY=...
# AWS_S3_REGION_NAME=us-east-1
# AWS_S3_CUSTOM_DOMAIN=   # optional, e.g. cdn.bobdyinternational.com
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

**Why admin CSS loads but site CSS doesn’t:** Django collects admin static files from the `admin` app automatically. Your site’s CSS/JS (e.g. `static/css/hero-split.css`, `static/vendor/`) are only collected if the project **`static/`** folder exists in the same directory as `manage.py` and you run `collectstatic` from that directory. If `static/` is missing or you ran `collectstatic` from the wrong path, `staticfiles/` will contain `admin/` but not `css/` or `vendor/`, so `/static/admin/...` works but `/static/css/...` returns 404.

**Verify after collectstatic:** On the server, from the project root (where `manage.py` is):

```bash
ls -la static/                    # should show css/ vendor/ themes/
ls staticfiles/css/ staticfiles/admin/   # both should exist
curl -sI https://bobdyinternational.com/static/css/hero-split.css  # expect 200
```

If `staticfiles/css/` is missing, ensure the repo has `static/css/` (and `static/vendor/`, `static/themes/`) at project root, then run `collectstatic --noinput` again from that root.

**Static and media on S3:** When `AWS_STORAGE_BUCKET_NAME` is set in `.env`, both static and media files are stored in that bucket (`static/` and `media/` prefixes). `collectstatic --noinput` uploads static files to S3. Nginx does not need to serve `/static/` or `/media/` in that case; the app uses S3 URLs.

Create a superuser if needed:

```bash
python manage.py createsuperuser
```

---

## 6. Run Gunicorn (test)

From the project directory (where `manage.py` is). The repo includes a config at `deploy/gunicorn.conf.py`:

```bash
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.production
gunicorn -c deploy/gunicorn.conf.py config.wsgi:application
```

Visit `http://your-server-ip:8000` only if you temporarily allow it (e.g. for testing). Normally you’ll put Nginx in front (next step).

---

## 7. Systemd service (Gunicorn as a daemon)

Config files live in the project under **`deploy/`**. Create the unit file and set paths to your project root (same directory as `manage.py`).

**Example:** project at `/root/Mythee/siteforge/siteforge/siteforge` (run as root):

```bash
sudo nano /etc/systemd/system/siteforge.service
```

```ini
[Unit]
Description=SiteForge Gunicorn
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=/root/Mythee/siteforge/siteforge/siteforge
Environment="PATH=/root/Mythee/siteforge/siteforge/siteforge/venv/bin"
EnvironmentFile=/root/Mythee/siteforge/siteforge/siteforge/.env
ExecStart=/root/Mythee/siteforge/siteforge/siteforge/venv/bin/gunicorn -c deploy/gunicorn.conf.py config.wsgi:application

Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Use your own path if different; for a dedicated user, set `User=` and `Group=` to that user and put the app under e.g. `/home/siteforge/app/siteforge`.

If `EnvironmentFile` doesn’t load `.env` on your system, either fix the path so `EnvironmentFile=` points to your real `.env`, or remove that line and use explicit variables:

```ini
Environment=DJANGO_SETTINGS_MODULE=config.settings.production
Environment=SECRET_KEY=your-secret-key
Environment=ALLOWED_HOSTS=bobdyinternational.com,www.bobdyinternational.com,amberonlinestore.com,www.amberonlinestore.com
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

The project includes **`deploy/siteforge.nginx.conf`** as a template. You can **copy** it to Nginx and edit, or **symlink** after filling placeholders.

### Option A – Copy (recommended)

Copy the config, replace placeholders with your app path and domain, then enable:

```bash
# From your project root (where manage.py is), e.g.:
cd /root/Mythee/siteforge/siteforge/siteforge
APP_ROOT=/root/Mythee/siteforge/siteforge/siteforge
sudo cp deploy/siteforge.nginx.conf /etc/nginx/sites-available/siteforge
sudo sed -i "s|APP_ROOT|$APP_ROOT|g; s|SERVER_NAME|bobdyinternational.com www.bobdyinternational.com amberonlinestore.com www.amberonlinestore.com|g" /etc/nginx/sites-available/siteforge
sudo ln -s /etc/nginx/sites-available/siteforge /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Option B – Symlink from project

If your server path and domain are fixed, you can replace placeholders in the project file and symlink:

```bash
cd /root/Mythee/siteforge/siteforge/siteforge
sed -i "s|APP_ROOT|/root/Mythee/siteforge/siteforge/siteforge|g; s|SERVER_NAME|bobdyinternational.com www.bobdyinternational.com amberonlinestore.com www.amberonlinestore.com|g" deploy/siteforge.nginx.conf
sudo ln -sf /root/Mythee/siteforge/siteforge/siteforge/deploy/siteforge.nginx.conf /etc/nginx/sites-enabled/siteforge
sudo nginx -t
sudo systemctl reload nginx
```

**Recommendation:** Use **Option A** so the repo file stays a template and server-specific values stay only on the server.

---

## 9. SSL with Let’s Encrypt (recommended)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d bobdyinternational.com -d www.bobdyinternational.com -d amberonlinestore.com -d www.amberonlinestore.com
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
- **ALLOWED_HOSTS**: Ensure your domains (e.g. `bobdyinternational.com,www.bobdyinternational.com,amberonlinestore.com,www.amberonlinestore.com`) and server IP are in `ALLOWED_HOSTS` in `.env`.
- **S3 images not loading (local or production)**: By default the app uses signed (querystring) URLs for media. Browsers can block these or the URLs can be malformed. **Fix:** (1) In `.env` set `AWS_S3_QUERYSTRING_AUTH=false` so media URLs are plain (no signature). (2) In AWS S3: open your bucket → Permissions → Block public access: turn off for this bucket if you want public read. (3) Add a bucket policy allowing public GetObject, e.g. `{"Version":"2012-10-17","Statement":[{"Sid":"PublicRead","Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":"arn:aws:s3:::YOUR_BUCKET_NAME/media/*"}]}`. (4) If you keep signed URLs, add CORS to the bucket for your origins (e.g. `https://bobdyinternational.com`, `https://amberonlinestore.com`, `http://bobdy:8000`). Then restart the app (`sudo systemctl restart siteforge`).

If you use **PostgreSQL** later, set `DATABASE_URL` (or equivalent) in `.env` and switch `config.settings.base` to use it; the same deployment steps apply.
