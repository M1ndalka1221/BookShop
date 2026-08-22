# Task 1 Brief: Environment Setup & Settings Configuration

**Files:**
- Modify: `requirements.txt`
- Modify: `core/settings.py`

**Requirements:**
1. Append the following packages to `requirements.txt`:
   - `djangorestframework`
   - `djangorestframework-simplejwt`
   - `django-filter`
   - `drf-spectacular`
   - `django-cors-headers`
2. Install them into the virtual environment using command:
   `.\.venv\Scripts\python.exe -m pip install djangorestframework djangorestframework-simplejwt django-filter drf-spectacular django-cors-headers`
3. In `core/settings.py`:
   - Add `'rest_framework'`, `'rest_framework_simplejwt'`, `'django_filters'`, `'drf_spectacular'`, `'corsheaders'` to `INSTALLED_APPS`.
   - Add `'corsheaders.middleware.CorsMiddleware'` to `MIDDLEWARE` right before `'django.middleware.common.CommonMiddleware'`.
   - Add `CORS_ALLOW_ALL_ORIGINS = True`.
   - Add `REST_FRAMEWORK`:
     ```python
     REST_FRAMEWORK = {
         'DEFAULT_AUTHENTICATION_CLASSES': (
             'rest_framework_simplejwt.authentication.JWTAuthentication',
             'rest_framework.authentication.SessionAuthentication',
         ),
         'DEFAULT_PERMISSION_CLASSES': (
             'rest_framework.permissions.IsAuthenticatedOrReadOnly',
         ),
         'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
         'PAGE_SIZE': 20,
         'DEFAULT_FILTER_BACKENDS': (
             'django_filters.rest_framework.DjangoFilterBackend',
             'rest_framework.filters.SearchFilter',
             'rest_framework.filters.OrderingFilter',
         ),
         'DEFAULT_THROTTLING_CLASSES': [
             'rest_framework.throttling.AnonRateThrottle',
             'rest_framework.throttling.UserRateThrottle',
         ],
         'DEFAULT_THROTTLING_RATES': {
             'anon': '100/minute',
             'user': '1000/minute',
         },
         'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
     }
     ```
   - Add `SPECTACULAR_SETTINGS`:
     ```python
     SPECTACULAR_SETTINGS = {
         'TITLE': 'BookShop API',
         'DESCRIPTION': 'BookShop REST API documentation',
         'VERSION': '1.0.0',
         'SERVE_INCLUDE_SCHEMA': False,
     }
     ```
4. Verify tests pass: `.\.venv\Scripts\python.exe -m pytest`
5. Commit changes: `git add requirements.txt core/settings.py` and `git commit -m "feat(api): add drf dependencies, CORS, JWT, throttling, and pagination settings"`
