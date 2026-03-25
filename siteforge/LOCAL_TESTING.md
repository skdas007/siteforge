# Local testing: Superadmin → Client → Upload content

With the site running on **http://localhost:8000**, you can test the full flow in two ways.

---

## Option A: One-command demo (fastest)

1. **Start the server** (if not already):
   ```bash
   cd siteforge && python manage.py runserver
   ```

2. **Create a demo client and user**:
   ```bash
   python manage.py create_demo_client
   ```
   This creates:
   - A **User** `client` with password `client123` (or use `--username` / `--password`)
   - A **Client** for domain `localhost` linked to that user (use `--domain 127.0.0.1` if you open the site via 127.0.0.1:8000)
   - A **Theme** if none exist

3. **Test as the client**:
   - Open **http://localhost:8000/** → you should see the demo client’s site (hero “Welcome to our site”).
   - Go to **http://localhost:8000/accounts/login/** → log in as `client` / `client123`.
   - Go to **http://localhost:8000/dashboard/** → open **Settings** and change hero title/subtitle, upload logo or banner, pick a theme, save.
   - Open **http://localhost:8000/** again → your changes appear on the public site.

---

## Option B: Manual setup (superadmin in Django admin)

1. **Create a superuser** (if you don’t have one):
   ```bash
   python manage.py createsuperuser
   ```

2. **Start the server** and open Django admin: **http://localhost:8000/admin/**  
   Log in with the superuser.

3. **Create a Theme** (if none exist):
   - **Themes** → **Add Theme** → e.g. Name: `Default`, Slug: `default`, **Is active** ✓ → Save.

4. **Create a client user**:
   - **Users** (under Authentication and Authorization) → **Add user** → e.g. Username: `myclient`, Password: `...` → Save.
   - Optionally set **Email** and **Active** ✓.

5. **Create a Client** and link the user:
   - **Tenants** → **Clients** → **Add Client**:
     - **Business name**: e.g. `My Store`
     - **Slug**: e.g. `my-store` (auto from business name)
     - **Domain**: `localhost` (must match how you open the site; use `127.0.0.1` if you use that in the browser)
     - **Theme**: select the theme you created
     - **User**: select the user you created (so they can log in to the dashboard)
     - **Is active** ✓ → Save.

6. **Test as the client**:
   - Open **http://localhost:8000/** (or http://127.0.0.1:8000/ if domain is `127.0.0.1`) → public site for that client.
   - **http://localhost:8000/accounts/login/** → log in with the client user.
   - **http://localhost:8000/dashboard/** → **Settings** → edit hero, upload logo/banner, save → reload home to see content.

---

## Important for localhost

- **Domain** in the Client must match the host you use in the browser:
  - **http://localhost:8000** → Client **domain** = `localhost`
  - **http://127.0.0.1:8000** → Client **domain** = `127.0.0.1`
- If you get “No site is configured for this domain” on the home page, add a Client with that domain (or run `create_demo_client --domain 127.0.0.1`).
- Dashboard and login URLs are the same for all tenants; access is controlled by the **logged-in user** and their linked **Client**.

---

## Testing a custom domain locally (e.g. `bobdy`)

If you created a Client with **domain** = `bobdy`, the browser must send `Host: bobdy` so the app can resolve that client.

1. **Point the hostname to your machine**  
   Add this line to your hosts file:
   - **Linux / macOS:** `sudo nano /etc/hosts`
   - **Windows:** `C:\Windows\System32\drivers\etc\hosts` (edit as Administrator)  
   Add:
   ```
   127.0.0.1   bobdy
   ```
   Save and close.

2. **Allow the host in Django**  
   If you use `config.settings.development`, `ALLOWED_HOSTS` already allows all hosts.  
   If you use base settings only, set in `.env`: `ALLOWED_HOSTS=localhost,127.0.0.1,bobdy`

3. **Open the site**  
   In the browser go to: **http://bobdy:8000/**  
   You should see the client you created with domain `bobdy`.  
   Login: **http://bobdy:8000/accounts/login/**  
   Dashboard: **http://bobdy:8000/dashboard/**


