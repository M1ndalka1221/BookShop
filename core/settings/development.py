"""
Development settings for BookShop project.
"""

import os
from .base import *

DEBUG = True

allowed_hosts_env = os.getenv('ALLOWED_HOSTS')
ALLOWED_HOSTS = [h.strip() for h in allowed_hosts_env.split(',')] if allowed_hosts_env else ['*']

INSTALLED_APPS += [
    'debug_toolbar',
]

# Insert DebugToolbarMiddleware after WhiteNoiseMiddleware
if 'whitenoise.middleware.WhiteNoiseMiddleware' in MIDDLEWARE:
    insert_idx = MIDDLEWARE.index('whitenoise.middleware.WhiteNoiseMiddleware') + 1
else:
    insert_idx = 1

MIDDLEWARE.insert(insert_idx, 'debug_toolbar.middleware.DebugToolbarMiddleware')

INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
CORS_ALLOW_ALL_ORIGINS = True
