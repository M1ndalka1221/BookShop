import pytest
from unittest.mock import patch
from django.test import Client


@pytest.fixture
def client():
    return Client()


@pytest.mark.django_db
def test_health_check_healthy(client):
    response = client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["components"]["database"] == "ok"
    assert data["components"]["cache"] == "ok"


@pytest.mark.django_db
def test_api_health_check_route(client):
    response = client.get("/api/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.django_db
@patch("django.db.connection.ensure_connection")
def test_health_check_db_failure(mock_ensure_connection, client):
    mock_ensure_connection.side_effect = Exception("DB Connection refused")
    response = client.get("/health/")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert "error" in data["components"]["database"]


@pytest.mark.django_db
@patch("django.core.cache.cache.set")
def test_health_check_cache_failure(mock_cache_set, client):
    mock_cache_set.side_effect = Exception("Redis connection refused")
    response = client.get("/health/")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert "error" in data["components"]["cache"]
