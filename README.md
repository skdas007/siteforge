# SiteForge — Multi-Client Website Platform

Phase 1 complete. See [PLAN.md](PLAN.md) for the full build plan.

## Setup

```bash
# From project root (my_project)
python3 -m venv venv
source venv/bin/activate   # Linux/macOS; on Windows: venv\Scripts\activate
pip install -r siteforge/requirements/base.txt

cd siteforge
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000/ and http://127.0.0.1:8000/admin/ (create a superuser with `python manage.py createsuperuser` first).

## Layout

- **venv** — at project root (`my_project/venv`)
- **siteforge/** — Django project (config, apps, static, templates)
- **siteforge/requirements/** — base.txt, dev.txt, production.txt
- **siteforge/env.example** — copy to `.env` and set values
