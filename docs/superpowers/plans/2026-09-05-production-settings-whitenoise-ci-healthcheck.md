# Production Settings, WhiteNoise, CI/CD, and Health Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modularize Django settings into base/development/production environments, configure WhiteNoise for static file serving via Gunicorn, implement a robust health check endpoint, and establish a complete GitHub Actions CI/CD pipeline with Docker Hub publishing.

**Architecture:** Split `core/settings.py` into `core/settings/` package (`base.py`, `development.py`, `production.py`, `__init__.py`) preserving backwards-compatible imports; inject WhiteNoise middleware into the HTTP pipeline; create `/health/` inspecting database and Redis connections; configure `.github/workflows/django.yml` with linting, testing, and Docker Hub deployment.

**Tech Stack:** Django 5.2, Python 3.11, WhiteNoise 6.6+, Gunicorn, PostgreSQL 15, Redis 7, Celery 5.6, GitHub Actions, Docker Hub.

**Spec:** `docs/superpowers/specs/2026-09-05-production-settings-whitenoise-ci-healthcheck-design.md`

## Global Constraints
- Target Docker Hub Username: `Mindalka`
- Target Docker Hub Image: `mindalka/bookshop:latest` and `mindalka/bookshop:${{ github.sha }}`
- Settings package backwards compatibility: `DJANGO_SETTINGS_MODULE = 'core.settings'` must resolve dynamically based on `DJANGO_ENV`
- Linter standards: `black` formatter, `flake8` with `max-line-length = 120` and migration exclusions

---

### Task 1: Add WhiteNoise to Dependencies and Base Configuration

**Files:**
- Modify: `requirements.txt`
- Modify: `Dockerfile`
- Test: container rebuild and static assets verification

**Interfaces:**
- Consumes: Django static assets under `static/` and collected into `staticfiles/`
- Produces: `whitenoise.middleware.WhiteNoiseMiddleware`, `whitenoise.storage.CompressedStaticFilesStorage`

- [ ] **Step 1: Add `whitenoise>=6.6.0` to requirements.txt**
  Add `whitenoise>=6.6.0` to `requirements.txt`.

- [ ] **Step 2: Verify package installation in Docker**
  Rebuild Docker images: `docker compose build web`.

- [ ] **Step 3: Commit dependency update**
  `git add requirements.txt`
  `git commit -m "build(deps): add whitenoise to requirements.txt"`

---

### Task 2: Split and Modularize Settings (`base`, `development`, `production`)

**Files:**
- Create: `core/settings/__init__.py`
- Create: `core/settings/base.py`
- Create: `core/settings/development.py`
- Create: `core/settings/production.py`
- Delete: `core/settings.py`
- Modify: `core/urls.py`

**Interfaces:**
- Consumes: Environment variables (`DJANGO_ENV`, `SECRET_KEY`, `ALLOWED_HOSTS`, `DB_*`, `REDIS_URL`, `SECURE_*`)
- Produces: Module configurations importing from `core.settings`, `core.settings.development`, `core.settings.production`

- [ ] **Step 1: Create `core/settings/base.py`**
  Migrate shared settings from `core/settings.py`. Add `whitenoise.middleware.WhiteNoiseMiddleware` after `SecurityMiddleware`. Configure `STORAGES` for WhiteNoise.
- [ ] **Step 2: Create `core/settings/development.py`**
  Inherit `base.py`, set `DEBUG = True`, configure `debug_toolbar`, allow hosts `['*']`, console email.
- [ ] **Step 3: Create `core/settings/production.py`**
  Inherit `base.py`, set `DEBUG = False`, configure security headers (`SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_*`, `X_FRAME_OPTIONS = 'DENY'`), strict secret loading.
- [ ] **Step 4: Create `core/settings/__init__.py`**
  Implement dynamic dispatcher based on `os.getenv('DJANGO_ENV', 'development')`.
- [ ] **Step 5: Clean up `core/urls.py` and remove old `core/settings.py`**
  Remove redundant `static()` hack in `core/urls.py` as WhiteNoise serves `/static/` automatically. Remove `core/settings.py`.
- [ ] **Step 6: Run test suite to verify settings**
  Execute `docker compose exec -T web pytest`.
- [ ] **Step 7: Commit settings modularization**
  `git add core/settings/ core/urls.py`
  `git commit -m "feat(settings): split settings into base, development, and production with whitenoise"`

---

### Task 3: Implement Health Check Endpoint & Unit Tests

**Files:**
- Create: `core/views.py`
- Create: `core/tests.py`
- Modify: `core/urls.py`

**Interfaces:**
- Consumes: `django.db.connection`, `django.core.cache.cache`
- Produces: `GET /health/` and `GET /api/health/` returning JSON status

- [ ] **Step 1: Write tests for health check in `core/tests.py`**
  Test healthy state (HTTP 200, status "healthy", DB ok, cache ok).
  Test DB failure (mock connection error -> HTTP 503, status "unhealthy").
  Test Cache failure (mock cache error -> HTTP 503, status "unhealthy").
- [ ] **Step 2: Run test to verify it fails (missing view)**
  Execute `docker compose exec -T web pytest core/tests.py`.
- [ ] **Step 3: Implement `health_check` view in `core/views.py`**
  Check `connection.ensure_connection()` and cache read/write. Return JsonResponse with 200 or 503.
- [ ] **Step 4: Wire routes in `core/urls.py`**
  Add paths `health/` and `api/health/`.
- [ ] **Step 5: Run tests to verify they pass**
  Execute `docker compose exec -T web pytest core/tests.py`.
- [ ] **Step 6: Commit health check endpoint**
  `git add core/views.py core/tests.py core/urls.py`
  `git commit -m "feat(api): add health check endpoint for db and cache monitoring"`

---

### Task 4: Configure Linters (`flake8`, `black`)

**Files:**
- Create: `.flake8`
- Modify: existing codebase files as needed for clean formatting

**Interfaces:**
- Consumes: Python source code across repository
- Produces: Clean linting output (0 errors)

- [ ] **Step 1: Create `.flake8` configuration file**
  Set `max-line-length = 120`, exclude migrations, `.venv`, `.git`, `docs`.
- [ ] **Step 2: Run `black --check .` and format if needed**
  Format files with `black .` so `black --check .` passes cleanly.
- [ ] **Step 3: Run `flake8 .` and resolve any warnings**
- [ ] **Step 4: Commit linter config and formatting**
  `git add .flake8`
  `git commit -m "style: configure flake8 and format code with black"`

---

### Task 5: Implement GitHub Actions CI/CD Pipeline

**Files:**
- Create: `.github/workflows/django.yml`

**Interfaces:**
- Consumes: GitHub Secrets (`DOCKERHUB_TOKEN`) and environment
- Produces: Automated linting, testing, and Docker Hub image build/push

- [ ] **Step 1: Create `.github/workflows/django.yml`**
  Define workflow on `push` and `pull_request` for `main`.
  Add `lint` job: `black --check .`, `flake8 .`.
  Add `test` job: runs PostgreSQL 15 & Redis 7 services, installs requirements, executes `pytest --cov`.
  Add `docker-build-push` job: runs on push to `main`, logs in with user `Mindalka` and `secrets.DOCKERHUB_TOKEN`, builds and pushes `mindalka/bookshop:latest` and `mindalka/bookshop:${{ github.sha }}`.
- [ ] **Step 2: Validate workflow syntax**
- [ ] **Step 3: Commit workflow file**
  `git add .github/workflows/django.yml`
  `git commit -m "ci: add GitHub Actions pipeline for linting, testing, and Docker Hub push"`

---

### Task 6: End-to-End Verification Across Environments

**Files:**
- Test: Full container environment verification
- Test: Dev settings, prod settings, static assets, health check, full test suite

- [ ] **Step 1: Rebuild and start all containers**
  Run `docker compose down && docker compose up -d --build`.
- [ ] **Step 2: Test `/health/` endpoint**
  Verify `curl.exe http://localhost:8000/health/` returns `{"status": "healthy", ...}`.
- [ ] **Step 3: Test WhiteNoise static serving**
  Verify `curl.exe -I http://localhost:8000/static/css/style.css` returns 200 OK with WhiteNoise headers.
- [ ] **Step 4: Run full test suite with coverage**
  Execute `docker compose exec -T web pytest`. Verify all tests pass.
