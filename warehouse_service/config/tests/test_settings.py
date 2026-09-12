from django.conf import settings


def test_settings_loaded():
    assert settings.configured is True
    assert "warehouse.apps.WarehouseConfig" in settings.INSTALLED_APPS
    assert "users.apps.UsersConfig" in settings.INSTALLED_APPS
    assert "rest_framework" in settings.INSTALLED_APPS
    assert "rest_framework_simplejwt" in settings.INSTALLED_APPS
    assert "drf_spectacular" in settings.INSTALLED_APPS


def test_auth_user_model():
    assert settings.AUTH_USER_MODEL == "users.CustomUser"


def test_celery_configuration():
    assert hasattr(settings, "CELERY_BROKER_URL")
    assert "release-expired-reservations-5m" in settings.CELERY_BEAT_SCHEDULE
