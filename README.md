# GoldVault — PhD Digital Library Platform

A premium academic digital library for PhD students and researchers. Built with Django, DRF, Bootstrap 5, and vanilla JavaScript.

---

## 🚀 Quick Start (5 minutes)

### Prerequisites
- Python 3.10+
- pip

### 1. Create virtual environment & install dependencies

```bash
cd phd_library
python -m venv venv

# Activate
source venv/bin/activate          # macOS/Linux
venv\Scripts\activate             # Windows

pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env if needed — defaults use SQLite so no DB setup required
```

### 3. Run migrations

```bash
python manage.py migrate
```

### 4. Seed sample data

```bash
python manage.py seed_data
```

This creates:
- **Admin:** `admin@scholarvault.com` / `admin123`
- **PhD User:** `phd@scholarvault.com` / `phd123`
- 8 categories + 12 sample publications

### 5. Start the server

```bash
python manage.py runserver
```

Open: **http://127.0.0.1:8000**

---

## 🌐 Pages

| URL | Description |
|-----|-------------|
| `/` | Landing page with hero search & featured publications |
| `/catalogue/` | AJAX search & filter library catalogue |
| `/publication/<slug>/` | Publication detail with citations |
| `/dashboard/` | User dashboard (login required) |
| `/auth/login/` | Sign in |
| `/auth/register/` | Create account |
| `/manage/` | Admin publication management (staff only) |
| `/admin/` | Django admin panel |
| `/api/` | DRF browsable API |

---

## 🔌 Key API Endpoints

```
GET  /api/publications/search/?q=&category=&type=&year_from=&year_to=&open_access=&sort=
GET  /api/publications/<slug>/
GET  /api/publications/featured/
GET  /api/categories/
POST /api/bookmarks/toggle/<slug>/
GET  /api/autocomplete/?q=
GET  /api/stats/
POST /api/auth/token/              (JWT)
POST /api/auth/token/refresh/      (JWT refresh)
```

---

## 🗄️ Using PostgreSQL (Optional)

1. Create database:
```sql
CREATE DATABASE scholarvault;
```

2. Update `.env`:
```env
USE_SQLITE=False
DB_NAME=scholarvault
DB_USER=your_user
DB_PASSWORD=your_password
```

3. Re-run migrations:
```bash
python manage.py migrate
python manage.py seed_data
```

---

## 🏗️ Project Structure

```
phd_library/
├── phd_library/          # Django project config
│   ├── settings.py
│   └── urls.py
├── users/                # Custom user model & auth
│   ├── models.py
│   ├── views.py
│   └── urls.py
├── library/              # Core library app
│   ├── models.py         # Publication, Category, Bookmark
│   ├── views.py          # All views (CBV)
│   └── management/commands/seed_data.py
├── api/                  # DRF REST API
│   ├── serializers.py
│   ├── views.py
│   ├── filters.py
│   └── urls.py
├── templates/            # HTML templates
│   ├── base.html
│   ├── library/          # Landing, catalogue, detail, dashboard
│   ├── auth/             # Login, register
│   ├── users/            # Profile
│   ├── admin_panel/      # Custom admin views
│   └── components/       # Reusable card component
├── static/
│   ├── css/main.css       # Full design system
│   └── js/
│       ├── main.js        # Navbar, search overlay, toasts
│       ├── landing.js     # Carousel, hero autocomplete
│       ├── catalogue.js   # AJAX search/filter engine
│       └── detail.js      # Detail page extras
├── media/                # User uploads
└── requirements.txt
```

---

## 🎨 Design System

- **Fonts:** Playfair Display (headings) + DM Sans (body)
- **Primary Color:** Deep Navy `#1B3A6B`
- **Accent:** Antique Gold `#C9A84C`
- **Framework:** Bootstrap 5.3 + custom CSS variables

---

## ✨ Features

- ⚡ **AJAX Live Search** — debounced real-time search with autocomplete
- 🔍 **Multi-Filter System** — category, type, year range, author, open access
- 📚 **Full Publication Detail** — tabs for abstract, details, citations (APA/MLA)
- 🔖 **Bookmarks** — save publications to personal library
- 📥 **Secure Downloads** — protected file serving with login + access control
- 👤 **User Dashboard** — bookmarks, history, recommendations
- 🎠 **Featured Carousel** — touch/drag-enabled publication showcase
- 📱 **Fully Responsive** — mobile-first design

---

## 🔒 Authentication

- Session-based for templates (Django built-in)
- JWT tokens for API (via `POST /api/auth/token/`)
- Register via `/auth/register/` or API

---

## 📦 Production Deployment

```bash
# Set environment variables
export DEBUG=False
export DJANGO_SECRET_KEY=your-production-key
export USE_SQLITE=False  # Use PostgreSQL

# Collect static files
python manage.py collectstatic --noinput

# Run with gunicorn
gunicorn phd_library.wsgi:application --bind 0.0.0.0:8000 --workers 4
```
