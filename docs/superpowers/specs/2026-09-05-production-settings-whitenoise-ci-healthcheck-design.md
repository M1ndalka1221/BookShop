# Design Specification: Production Settings, WhiteNoise, CI/CD, and Health Check

- **Date**: 2026-09-05
- **Status**: Approved by User
- **Target Repository**: BookShop (Django + Celery + PostgreSQL + Redis)

## 1. Overview & Objectives

This specification defines the architectural enhancements required for production-readiness:
1. **Settings Modularization**: Split monolithic `core/settings.py` into a structured package (`core/settings/`) supporting `base`, `development`, and `production` environments while preserving seamless backwards compatibility.
2. **Production Hardening**: Configure `DEBUG=False`, security headers (HSTS, SSL redirect, secure cookies, X-Frame-Options), and strict environment variable validation via `.env`.
3. **High-Performance Static Assets**: Integrate `whitenoise` to serve static files reliably directly through Gunicorn/WSGI in containerized environments.
4. **Health Check Endpoint**: Provide `/health/` and `/api/health/` endpoints reporting live connectivity status for PostgreSQL and Redis with appropriate HTTP status codes (200 OK / 503 Service Unavailable).
5. **GitHub Actions CI/CD**: Implement `.github/workflows/django.yml` automating code linting (`flake8`, `black`), testing (`pytest` with coverage), and Docker Hub image build & push (`Mindalka/bookshop:latest` and SHA tag on pushes to `main`).

---

## 2. Settings Architecture

### 2.1 Directory Structure
Convert `core/settings.py` into a package:
```text
core/
└── settings/
    ├── __init__.py
    ├── base.py
    ├── development.py
    └── production.py
```

### 2.2 Component Roles
- **`base.py`**:
  - Contains shared configuration: `BASE_DIR`, `SECRET_KEY` fallback for development, `INSTALLED_APPS` (core Django apps, REST framework, Spectacular, CORS, users, catalog), `TEMPLATES`, `AUTH_PASSWORD_VALIDATORS`, `LANGUAGE_CODE`, `LANGUAGES`, `TIME_ZONE`, `USE_I18N`, `USE_TZ`, `LOCALE_PATHS`, `STATIC_URL`, `STATIC_ROOT`, `STATICFILES_DIRS`, `STORAGES` (WhiteNoise storage), Celery broker/backend settings, DRF configuration, Spectacular settings.
  - Middlewares: Includes `SecurityMiddleware`, `WhiteNoiseMiddleware`, `CorsMiddleware`, `SessionMiddleware`, `LocaleMiddleware`, `CommonMiddleware`, `CsrfViewMiddleware`, `AuthenticationMiddleware`, `MessageMiddleware`, `XFrameOptionsMiddleware`.
  - Database & Cache: Base connection definitions reading from environment variables (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `REDIS_URL`).

- **`development.py`**:
  - Inherits from `base.py` (`from .base import *`).
  - Sets `DEBUG = True`.
  - Appends `debug_toolbar` to `INSTALLED_APPS` and `DebugToolbarMiddleware` to `MIDDLEWARE`.
  - Configures `INTERNAL_IPS = ["127.0.0.1"]`.
  - Permissive `ALLOWED_HOSTS = ['*']` and `CORS_ALLOW_ALL_ORIGINS = True`.
  - Console email backend: `EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'`.

- **`production.py`**:
  - Inherits from `base.py` (`from .base import *`).
  - Sets `DEBUG = False`.
  - Strictly reads `SECRET_KEY` from environment (raising an error if missing or defaulting in production).
  - Parses `ALLOWED_HOSTS` from `os.getenv('ALLOWED_HOSTS', '')` as a comma-separated list.
  - Enforces production security headers:
    ```python
    SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True').lower() == 'true'
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True').lower() == 'true'
    CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'True').lower() == 'true'
    SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
    ```
  - Sentry initialization if `SENTRY_DSN` is set.
  - Email backend configurable via environment variables (e.g. SMTP).

- **`__init__.py`**:
  - Dynamically detects the target environment via `os.getenv('DJANGO_ENV', 'development')`:
    ```python
    import os
    env = os.getenv('DJANGO_ENV', 'development').lower()
    if env == 'production':
        from .production import *
    else:
        from .development import *
    ```
  - Ensures full backwards-compatibility with `DJANGO_SETTINGS_MODULE = 'core.settings'`.

---

## 3. WhiteNoise Static Asset Serving

### 3.1 Dependencies
Add `whitenoise>=6.6.0` to `requirements.txt`.

### 3.2 Configuration
1. Place `'whitenoise.middleware.WhiteNoiseMiddleware'` immediately following `'django.middleware.security.SecurityMiddleware'` in `base.py`.
2. Configure `STORAGES`:
   ```python
   STORAGES = {
       "default": {
           "BACKEND": "django.core.files.storage.FileSystemStorage",
       },
       "staticfiles": {
           "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
       },
   }
   ```
3. Set `WHITENOISE_USE_FINDERS = True` during development/fallback, and enable Gzip/Brotli compression in production.
4. Clean up `core/urls.py` so WhiteNoise handles `/static/` automatically in both WSGI (Gunicorn) and ASGI environments, removing unnecessary manual static hooks.

---

## 4. Health Check Endpoint

### 4.1 Endpoint Route
- URL: `GET /health/` and `GET /api/health/`
- Target view: `core.views.health_check`

### 4.2 Health Check Logic
1. **Database Check**: Executes `django.db.connection.ensure_connection()` to test database connectivity.
2. **Cache / Redis Check**: Executes `django.core.cache.cache.set('_health_check', '1', timeout=5)` and verifies the value via `cache.get('_health_check')`.
3. **Response Structure**:
   - Success (HTTP 200):
     ```json
     {
       "status": "healthy",
       "components": {
         "database": "ok",
         "cache": "ok"
       }
     }
     ```
   - Failure (HTTP 503 Service Unavailable):
     ```json
     {
       "status": "unhealthy",
       "components": {
         "database": "error: <details>",
         "cache": "ok"
       }
     }
     ```
4. **Security / Throttling**: Exempt `/health/` from authentication and CSRF; keep it lightweight for container orchestration and uptime monitoring.

---

## 5. GitHub Actions CI/CD Pipeline

### 5.1 File Location
`.github/workflows/django.yml`

### 5.2 Triggers
- `push` to `main`
- `pull_request` targeting `main`

### 5.3 Jobs
1. **`lint`**:
   - Runner: `ubuntu-latest`
   - Steps:
     - Checkout code
     - Set up Python 3.11 with pip caching
     - Install `flake8`, `black`
     - Run `black --check .`
     - Run `flake8 .` (using `.flake8` config ignoring migrations and max-line-length=120)
2. **`test`**:
   - Runner: `ubuntu-latest`
   - Services:
     - PostgreSQL 15 (`postgres_db`, user `postgres_user`, password `supersecretpassword`)
     - Redis 7
   - Steps:
     - Checkout code
     - Set up Python 3.11 with pip caching
     - Install system dependencies (`libpq-dev`, etc.) and `requirements.txt`
     - Run `pytest --cov=.`
3. **`docker-build-push`**:
   - Depends on: `[lint, test]`
   - Condition: `github.event_name == 'push' && github.ref == 'refs/heads/main'`
   - Runner: `ubuntu-latest`
   - Steps:
     - Checkout code
     - Set up Docker Buildx
     - Log in to Docker Hub using:
       - Username: `Mindalka`
       - Password: `${{ secrets.DOCKERHUB_TOKEN }}`
     - Build and push:
       - Image tags: `mindalka/bookshop:latest`, `mindalka/bookshop:${{ github.sha }}`

---

## 6. Linter & Tooling Configuration

- Create `.flake8`:
  ```ini
  [flake8]
  max-line-length = 120
  exclude =
      .git,
      __pycache__,
      */migrations/*,
      .venv,
      htmlcov,
      .pytest_cache,
      docs
  ignore = E203, W503
  ```
- Format code with `black` so the initial lint job succeeds cleanly without formatting discrepancies.

---

## 7. Verification Plan

1. **Unit & Integration Tests**:
   - Add tests for `health_check` endpoint (HTTP 200 on healthy, error handling).
   - Ensure all existing 81 tests pass under new settings package: `pytest`.
2. **WhiteNoise Verification**:
   - Run `python manage.py collectstatic --noinput`.
   - Start Gunicorn and request `/static/css/style.css` without Django `DEBUG=True` static routing. Verify HTTP 200 with appropriate cache and compression headers.
3. **Settings Verification**:
   - Verify `DJANGO_ENV=development` enables `DEBUG` and debug toolbar.
   - Verify `DJANGO_ENV=production` sets `DEBUG=False` and enables security headers.
4. **Local Lint Check**:
   - Run `black --check .` and `flake8 .` locally to ensure CI will pass cleanly.
