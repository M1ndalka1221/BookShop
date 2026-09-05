"""
Settings environment dispatcher.
Dynamically loads production or development settings based on DJANGO_ENV.
Defaults to development.
"""

import os

env = os.getenv("DJANGO_ENV", "development").strip().lower()

if env == "production":
    from .production import *  # noqa: F401, F403
else:
    from .development import *  # noqa: F401, F403
