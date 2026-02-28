# Multi-Client Website Platform — Build Plan

**Stack:** Django · Django Templates · Bootstrap 5 (latest, downloaded) · SQLite (PostgreSQL later) · AWS S3 · Nginx + Gunicorn · Cloudflare CDN  
**Scope:** SaaS-style multi-tenant site builder, 1M monthly users target, no React.

---

## Progress

| Phase / Item | Status |
|--------------|--------|
| **Phase 1.1** Django project structure (siteforge/, config/, apps/, static/, templates/, requirements, env.example) | ✅ Done |
| **Phase 1.2** UI: Bootstrap 5 downloaded, no CDN; base template loads from `static/vendor/bootstrap/` | ✅ Done |
| **Phase 1.3** Multi-tenant resolution middleware | ✅ Done |
| **Phase 1.4** Configuration & secrets (env vars, env.example, SQLite in base settings) | ✅ Done |
| **Phase 1.5** Complete UI (public + dashboard templates, theme CSS, placeholder views) | ✅ Done |
| **Phase 2** Data models & migrations | ⏳ Partial (Theme + Client done; Product, ContactSubmission pending) |
| **Phase 3** Theme system | ⏳ Pending |
| **Phase 4** Public website flow | ⏳ Pending |
| **Phase 5** Client dashboard | ⏳ Pending |
| **Phase 6** Media & S3 | ⏳ Pending |
| **Phase 7** Security | ⏳ Pending |
| **Phase 8** Scalability | ⏳ Pending |
| **Phase 9** Deployment | ⏳ Pending |
| **Phase 10** Implementation order step 1 (scaffold) | ✅ Done |

---

## Phase 1: Project Setup & Core Architecture

### 1.1 Django Project Structure ✅

```
siteforge/
├── config/                 # Project config (settings, urls, wsgi)
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── core/               # Shared utilities, middleware, base templates
│   ├── tenants/            # Client model, tenant resolution, dashboard
│   ├── themes/             # Theme registry, CSS loading
│   ├── catalog/            # Product CRUD, ordering
│   └── leads/              # Contact form, submissions, notifications
├── static/
│   ├── vendor/
│   │   └── bootstrap/      # Downloaded Bootstrap 5 (css/, js/) — no CDN
│   ├── themes/             # Per-theme CSS (e.g. themes/default/, themes/minimal/)
│   └── css/                # Project-specific overrides if needed
├── templates/
│   ├── base.html           # Shared layout (theme-agnostic structure)
│   ├── public/             # Public site (home, contact)
│   └── dashboard/          # Client dashboard
├── manage.py
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── production.txt
└── env.example
```

- **Single Django project:** One codebase; multi-tenancy by domain, not by separate apps per client.
- **Stateless app servers:** No local file storage for media; all sessions/cache in Redis/DB.

### 1.2 UI: Bootstrap 5 (Downloaded, No CDN) ✅

- **Framework:** Bootstrap 5 only (latest 5.3.x) for faster, consistent UI development across public site and dashboard.
- **No CDN:** Do not use Bootstrap via CDN links. Download the official release and serve from our static files.
- **Download:** Use the compiled dist from [Bootstrap releases](https://github.com/twbs/bootstrap/releases) (e.g. `bootstrap-5.3.x-dist.zip`). Extract into `static/vendor/bootstrap/` so that:
  - `static/vendor/bootstrap/css/bootstrap.min.css` (and optional `bootstrap.min.css.map`)
  - `static/vendor/bootstrap/js/bootstrap.bundle.min.js` (includes Popper)
  are available. Optional: include RTL CSS if needed.
- **Templates:** In base layout, load Bootstrap with `{% static 'vendor/bootstrap/css/bootstrap.min.css' %}` and `{% static 'vendor/bootstrap/js/bootstrap.bundle.min.js' %}` before `</body>`.
- **Themes:** Theme CSS in `static/themes/<slug>/` should extend/override Bootstrap variables or classes; no duplicate layout framework. Easiest path: one shared Bootstrap base + theme-specific CSS on top.
- **Upgrades:** To upgrade Bootstrap, replace the contents of `static/vendor/bootstrap/` with a new dist download and run `collectstatic`; no build step required if using precompiled files.

### 1.3 Multi-Tenant Resolution ✅

- **Middleware:** `TenantResolutionMiddleware` (runs early).
  - Read `request.get_host()` (respect `X-Forwarded-Host` behind proxy).
  - Normalize domain (strip port, lowercase).
  - Look up `Client` by `domain` (or subdomain) with caching (see 7.2).
  - Attach `request.client` (or `request.tenant`); 404 if unknown/inactive.
- **Domain model:** One canonical domain per client (e.g. `client1.com` or `client1.platform.com`). Optional: `ClientDomain` table for multiple domains → one client.
- **Security:** Validate domain against allowlist; no arbitrary Host header trust without checks.
- **Implemented:** `apps.core.middleware.TenantResolutionMiddleware`; skips `/admin/`, `/dashboard/`, `/static/`, `/media/`. In DEBUG, unknown domain sets `request.client = None` so localhost works; in production returns 404. Theme and Client models added for resolution.

### 1.4 Configuration & Secrets ✅

- **Environment variables** for all secrets and environment-specific config:
  - `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
  - **Database:** Use **SQLite** for now (default `db.sqlite3` or path via `DATABASE_PATH`). Omit `DATABASE_URL` in development. For production later, set `DATABASE_URL` (PostgreSQL) and configure Django to use it (e.g. `django-environ` or conditional in settings); then migrate to PostgreSQL without app code changes.
  - `REDIS_URL` (optional for now; required for cache/sessions at scale)
  - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION`, `AWS_S3_CUSTOM_DOMAIN` (e.g. Cloudflare or S3)
  - `EMAIL_*`, `DEFAULT_FROM_EMAIL`
  - Optional: `SENTRY_DSN`, `CLOUDFLARE_*` if needed for API
- **`env.example`** documents every variable (no real values).

### 1.5 Complete UI (Before Models) ✅

Complete all templates and placeholder views so the UI is ready before implementing data models. Once the UI is in place, models and views can be wired without changing layout.

**Public site (templates + placeholder view):**
- **Base template (`templates/base.html`):** Shared layout; loads Bootstrap + theme CSS by `theme_slug` (default `static/themes/default/style.css`).
- **Home (`templates/public/home.html`):** Banner section (placeholder or image), hero (title + subtitle), products grid (placeholder list), contact form (name, email, phone, message); form POSTs to `contact_submit` (placeholder redirect until leads model exists).
- **URLs:** `/` (home), `/contact/` (POST only, placeholder).

**Dashboard (templates + placeholder views):**
- **Base dashboard (`templates/dashboard/base_dashboard.html`):** Navbar with links: Home, Site settings, Products, Leads; Django admin link.
- **Dashboard home:** Welcome + quick links to settings, products, leads.
- **Site settings (`/dashboard/settings/`):** Form sections: banner image upload, hero title/subtitle, logo upload, theme selector (Default / Minimal), contact email.
- **Products:** List (`/dashboard/products/`), Add (`/dashboard/products/add/`), Edit (`/dashboard/products/<id>/edit/`); table with order, image, name, price, active, actions; note for drag reorder (AJAX later).
- **Leads (`/dashboard/leads/`):** Read-only table: date, name, email, phone, message.
- **URLs:** `/dashboard/` (namespace `dashboard`), all views render with empty/placeholder context until models exist.

**Themes:**
- **`static/themes/default/style.css`** and **`static/themes/minimal/style.css`:** Minimal CSS overrides (e.g. `--sf-hero-bg`, `.sf-hero`). Base template includes theme by slug; adding more themes = adding more folders under `static/themes/<slug>/`.

**Implementation:** Placeholder views in `apps.core.views` (index, contact_submit) and `apps.tenants.views` (dashboard_*); no auth, no DB; context uses `request` attributes or empty lists. Next step is Phase 2 (models), then wire these views to real data.

---

## Phase 2: Data Models & Migrations

- **Database:** Use **SQLite** for development (Django default). Use only standard Django ORM and field types so the same models and migrations work on **PostgreSQL** later; avoid DB-specific raw SQL or SQLite-only features.
- **Later switch:** Point `DATABASE_URL` to PostgreSQL, run migrations, and (if needed) dump/load or sync data; no model changes required.

### 2.1 Core Models

**Client (tenants app)**

| Field | Type | Notes |
|-------|------|--------|
| user | OneToOne(User) | Login for dashboard |
| business_name | CharField | Display name |
| slug | SlugField | Unique, for URLs/theme paths if needed |
| domain | CharField | Unique, indexed (e.g. `client1.com`) |
| theme | FK(Theme) | Selected theme |
| banner_image | ImageField/URL | S3; optional placeholder |
| hero_title | CharField/TextField | |
| hero_subtitle | TextField | |
| logo | ImageField/URL | S3 |
| contact_email | EmailField | For form notifications |
| is_active | BooleanField | If false, 404 or maintenance page |
| created_at, updated_at | DateTimeField | |

**Theme (themes app)**

| Field | Type | Notes |
|-------|------|--------|
| name | CharField | Display name |
| slug | SlugField | Unique (e.g. `default`, `minimal`) |
| preview_image | ImageField/URL | S3, for dashboard picker |
| is_active | BooleanField | |

Theme CSS lives under `static/themes/<slug>/style.css` (or multiple files). No duplicate HTML; one base layout + theme CSS.

**Product (catalog app)**

| Field | Type | Notes |
|-------|------|--------|
| client | FK(Client) | Always set; part of tenant filter |
| name | CharField | |
| description | TextField | |
| price | DecimalField | |
| image | ImageField | S3 |
| order | PositiveIntegerField | For drag-and-drop ordering |
| is_active | BooleanField | |
| created_at, updated_at | DateTimeField | |

**ContactSubmission (leads app)**

| Field | Type | Notes |
|-------|------|--------|
| client | FK(Client) | Tenant scope |
| name | CharField | |
| email | EmailField | |
| phone | CharField | Optional |
| message | TextField | |
| created_at | DateTimeField | |

### 2.2 Tenant Isolation

- **All client-scoped queries** must filter by `client=request.client` (or current client from middleware).
- **Dashboard views:** Use a mixin or decorator that:
  - Requires login.
  - Resolves client from `request.user` (e.g. `request.user.client`) and ensures user can only see their client’s data.
- **Django admin:** Used as the primary way to update content and images (see §2.4). 

### 2.3 Product Ordering

- Use `order` (integer) for sorting. APIs/views:
  - **List:** `Product.objects.filter(client=client).order_by('order')`
  - **Reorder (dashboard):** Accept list of `product_id` in new order; update `order` in bulk (e.g. in a transaction). Use minimal AJAX (single endpoint) for drag-and-drop reorder.

### 2.4 Django Admin for Content and Images

- **Use Django admin** to create, update, and delete content and images. Staff/superusers manage everything from `/admin/`.
- **Registered models and capabilities:**
  - **Client:** Edit business name, domain, theme, **banner image**, **hero title/subtitle**, **logo**, contact email, is_active. File uploads (banner, logo) go to S3 via django-storages.
  - **Theme:** Name, slug, preview image (S3), is_active.
  - **Product:** Per-client; name, description, price, **image** (S3), order, is_active. Inline editing for a client’s products or list view with filters by client. Support **reorder** (e.g. admin action “Set order from list” or drag-and-drop in custom change_list if desired).
  - **ContactSubmission:** Read-only list/detail; filter by client; optional export.
- **Tenant isolation in admin:** Restrict non-superuser staff to their client(s) only (e.g. custom `ModelAdmin.get_queryset()` and form field limiting by client). Superuser sees all.
- **Media:** All image fields use the project’s default storage (S3 in production); admin uploads and in-dashboard uploads both go to S3. No local media in production.
- **Optional:** A separate client-facing dashboard (Phase 5) can mirror a subset of these edits for client users; Django admin remains the main back-office for content and images.

---

## Phase 3: Theme System

### 3.1 Single Shared Layout

- **One base template** (e.g. `templates/base.html` or `templates/public/base.html`):
  - Common structure: `html`, `head` (title, meta, base CSS), body, header (banner, logo, nav), main (hero block, content block), footer, contact form block.
  - **Theme CSS:** Include per-theme stylesheet: e.g. `{% static 'themes/'|add: client.theme.slug|add: '/style.css' %}` (or use a template tag that returns theme’s primary CSS URL).
- **No duplicate HTML per theme.** Only CSS and possibly small template fragments (e.g. optional “theme-specific partial”) if really needed later.

### 3.2 Storing Themes

- **Static files:** `static/themes/<slug>/style.css` (and optional `extra.css`, `variables.css`).
- **Optional:** Store theme slug in DB; path is always derived from slug. Adding 100+ themes = adding 100+ folders under `static/themes/`; no performance issue if we use CDN and cache headers.
- **Changing theme:** Client selects theme in dashboard → update `Client.theme_id` → next request loads new CSS. No deploy needed; change is immediate.

### 3.3 CDN for Static/Media

- **STATIC_URL / MEDIA_URL:** Point to Cloudflare (e.g. `https://cdn.yourplatform.com/`) or S3 + CloudFront.
- **Django:** Use `django-storages` for media (S3); static can be collected and served via CDN (e.g. `collectstatic` → upload to S3 or serve via Nginx with CDN in front).

---

## Phase 4: Public Website Flow

### 4.1 Request Flow

1. Request hits Nginx → (optional) Cloudflare → Gunicorn.
2. **TenantResolutionMiddleware:** Resolve client from Host; set `request.client`; return 404 if not found or inactive.
3. View loads **client** config (banner, hero, logo, theme, products, contact_email).
4. Render template with **client** and **theme** context; include theme CSS.
5. Output: Banner, hero, product list, contact form.

### 4.2 Caching (Per-Client)

- **Homepage (or key public pages):** Cache full HTML or fragment per `client.id` (and optionally by theme/last_updated). TTL e.g. 5–15 minutes; invalidate on client/content update.
- **Product list:** Cache queryset or rendered fragment per client.
- **Theme config:** Theme slug and paths are cheap; can be cached in request-level or Redis (key: `client:<id>:theme`).

### 4.3 Contact Form

- **POST** to same domain; CSRF enabled.
- **Validate:** name, email, message (and optional phone); rate limit by IP and/or by client.
- **Save:** `ContactSubmission(client=request.client, ...)`.
- **Notify:** Send email to `client.contact_email` (Celery task or sync in development). Template: “New contact from your site: …”.
- **Extensibility:** Same task can later call WhatsApp API or push to queue; keep handler in one place (e.g. `leads.tasks.notify_new_submission`).

---

## Phase 5: Client Dashboard

### 5.1 Access Control

- **Login:** Django auth; only users linked to a `Client` (OneToOne) can access dashboard.
- **URL:** e.g. `/dashboard/` (or subdomain like `app.platform.com`). Resolve client from `request.user.client`, not from Host, so dashboard can live on one domain.
- **Mixin:** `DashboardAuthMixin` — `login_required`, and set `self.client = request.user.client`; 404 if user has no client.

### 5.2 Dashboard Features (Django Templates)

- **Banner image:** Form with file upload → store in S3 via `django-storages`; save URL/path on `Client`.
- **Hero content:** Form fields for `hero_title`, `hero_subtitle`; save to `Client`.
- **Theme:** Dropdown/radio of active themes; POST to set `Client.theme`.
- **Products:** List with add/edit/delete (Django forms/templates). Optional: inline or modal forms; minimal AJAX for “quick edit” if desired.
- **Product reorder:** Drag-and-drop list; on drop, AJAX POST list of IDs in order → backend updates `order` for each `Product` (bulk update in transaction).
- **Contact submissions:** Read-only list (and detail) for `ContactSubmission.objects.filter(client=request.user.client).order_by('-created_at')`. Optional: export CSV (future).

All forms use Django templates; AJAX only for reorder (and optionally quick toggles).

---

## Phase 6: Media & Storage (S3)

### 6.1 Django-Storages (S3)

- **Default file storage:** `storages.backends.s3b3.S3Boto3Storage` (or S3Boto3Storage with custom domain).
- **Settings:** `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION_NAME`, `AWS_S3_CUSTOM_DOMAIN` (e.g. Cloudflare or CloudFront), `AWS_S3_OBJECT_PARAMETERS` (e.g. Cache-Control).
- **Media only on S3:** No `MEDIA_ROOT` on disk for production; all uploads go to S3. Local dev can use S3 or local storage via settings.

### 6.2 Upload Rules

- **Restrict file types:** e.g. image (PNG, JPEG, WebP); validate in form (content-type + extension) and optional size check before upload.
- **Restrict file size:** e.g. max 5 MB per file; enforce in view/form and optionally in Nginx.
- **Naming:** Use UUID or client-scoped path to avoid collisions and enumeration (e.g. `tenants/<client_id>/banner/<uuid>.<ext>`).

---

## Phase 7: Security

### 7.1 Checklist

- **HTTPS:** Enforce in Nginx and Django (`SECURE_SSL_REDIRECT`, `SECURE_PROXY_SSL_HEADER`).
- **Secrets:** Only in env; never in code/repo.
- **Cross-client access:** Every client-scoped view/API filters by `request.client` or `request.user.client`; no raw IDs from URL for other clients’ data.
- **Admin:** Strong passwords; restrict admin URL (e.g. `/secret-admin/`); rate limit and optional 2FA.
- **Domain validation:** Only serve known clients; reject unknown Host with 404 or custom “unknown tenant” page.
- **File upload:** Type and size limits; no execution of uploaded files; serve via CDN with safe content-type headers.

### 7.2 Domain Mapping

- Store only allowed domains in DB (`Client.domain` or `ClientDomain`). Middleware resolves client only for these; otherwise return 404. No dynamic “create site by Host” without prior registration.

---

## Phase 8: Scalability (1M Monthly Users)

### 8.1 Target Architecture

```
Users → Cloudflare CDN → Load Balancer → Multiple App Servers (Gunicorn)
                                        → Redis (cache + sessions)
                                        → PostgreSQL (primary + read replicas when scaled)
                                        → S3 (+ CDN) for media/static
```

- **Current development:** Use SQLite; no Redis required. When moving to production, add PostgreSQL and Redis as above.

- **Stateless app servers:** No local session storage; use Redis or DB for sessions. No local media.
- **Horizontal scaling:** Add more Gunicorn workers and more app nodes behind load balancer.

### 8.2 Caching Strategy

- **Redis:** Use for:
  - **Page/fragment cache:** e.g. `cache.get('public:home:client:%s' % client.id)` with TTL; invalidate on client/product/theme update.
  - **Session store:** `SESSION_ENGINE = 'django.contrib.sessions.backends.cache'` with Redis.
  - **Optional:** Theme config cache, “client by domain” lookup (short TTL or invalidate on client update).
- **Database:** Indexes on `Client.domain`, `Product(client_id, order)`, `ContactSubmission(client_id, created_at)`; avoid N+1 (select_related/prefetch_related for client + theme + products).

### 8.3 Query Optimization

- **Public homepage:** One query for client (with select_related('theme')), one for products (filter by client, order_by('order')); consider single query with prefetch if needed.
- **Dashboard:** Always filter by `request.user.client`; use pagination for submissions and product list.

### 8.4 CDN

- **Cloudflare (or similar):** In front of app and/or in front of S3/CloudFront.
- **Static/Media:** Served via CDN; long cache for theme CSS and images; versioning or cache busting via path/query if needed.

---

## Phase 9: Deployment (VPS, Nginx, Gunicorn, Cloudflare)

### 9.1 VPS

- One or more VPS instances; load balancer in front if multiple app servers.
- OS: Ubuntu 22.04 LTS (or similar); firewall (only 80/443 and SSH).

### 9.2 Nginx

- **SSL:** Terminate SSL or proxy to Cloudflare (Flexible/Full).
- **Proxy:** Reverse proxy to Gunicorn (e.g. `unix:/run/gunicorn.sock` or `127.0.0.1:8000`).
- **Static/Media:** Option A: proxy to Django in dev/small setup; Option B: alias to collected static and/or proxy to S3/CDN for media.
- **Client max body size:** e.g. `client_max_body_size 5M;` for uploads.
- **Rate limiting:** Optional `limit_req_zone` for login and contact form.

### 9.3 Gunicorn

- Run with multiple workers (e.g. `2 * CPU + 1`); bind to socket or localhost.
- Use **systemd** (or supervisor) to keep Gunicorn running; restart on failure.

### 9.4 Cloudflare

- **DNS:** Point domains to VPS or load balancer.
- **Proxy (orange cloud):** Enable for app and/or static/media to get DDoS protection and caching.
- **SSL:** Full (strict) if origin has valid cert; or Flexible if only Cloudflare has SSL.

### 9.5 App Deployment

- **Code:** Git pull or CI/CD; install deps from `requirements/production.txt`.
- **Migrations:** Run after deploy; zero-downtime migrations where possible (add columns nullable first, backfill, then add constraints).
- **Collectstatic:** Run and upload to S3 or copy to Nginx-served path.
- **Env:** Load from `.env` or systemd environment; never commit `.env`.

---

## Phase 10: Implementation Order (Suggested)

1. **Project scaffold:** Django project, apps (core, tenants, themes, catalog, leads), settings split, env.example. ✅
1.5. **Complete UI:** Public site (banner, hero, products, contact form) + dashboard (settings, products, leads) templates; theme CSS (default, minimal); placeholder views and URLs. No auth/DB yet. ✅
2. **Models:** Client, Theme, Product, ContactSubmission; migrations; Django admin for content and images (Client, Theme, Product, ContactSubmission).
3. **Tenant middleware:** Resolve client by domain; attach to request; 404 for unknown.
4. **Theme system:** Create 1–2 themes (CSS only); base template; include theme CSS by slug. ✅ (default + minimal theme CSS; base includes by slug.)
5. **Public site:** Home view (banner, hero, products, contact form); contact form POST and save + email. ✅ (UI done; backend when models exist.)
6. **S3:** Configure django-storages; media uploads to S3; use in Client (banner, logo) and Product (image).
7. **Dashboard auth:** Login, mixin, dashboard home.
8. **Dashboard CRUD:** Banner, hero, theme picker, products (add/edit/delete), reorder (AJAX), contact submissions list.
9. **Security pass:** HTTPS, upload limits, tenant checks, domain validation.
10. **Caching:** Redis; cache homepage and product list per client; session in Redis.
11. **Deployment:** Nginx, Gunicorn, systemd, Cloudflare; collectstatic and S3; env-based config.
12. **Scaling prep:** Document scaling (add app servers, Redis, DB tuning); add indexes and query checks.

---

## Deliverables Summary

| Item | Description |
|------|-------------|
| **Codebase** | Single Django project, multi-tenant by domain |
| **Models** | Client, Theme, Product, ContactSubmission; tenant isolation |
| **Public site** | Domain → client → theme → banner, hero, products, contact form |
| **Django admin** | Primary way to update content and images (Client, Theme, Product, ContactSubmission); S3 uploads; tenant isolation for staff. |
| **Dashboard** | Optional client-facing UI: login, edit banner/hero/theme, products CRUD + reorder, view submissions |
| **Themes** | CSS-only, one layout, many themes in `static/themes/<slug>/` |
| **Media** | All uploads to S3; CDN for delivery |
| **Security** | HTTPS, env secrets, upload limits, strict tenant isolation |
| **Scale** | Stateless app, Redis cache, CDN, DB indexes, 1M users ready |

**Next step:** Phase 2 (data models and migrations). Then Phase 1.3 (tenant middleware) and wire public/dashboard views to real data.
