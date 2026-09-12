import pytest
from rest_framework.test import APIClient
from rest_framework import status


@pytest.mark.django_db
def test_health_check_endpoint():
    client = APIClient()
    res = client.get("/health/")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["status"] == "ok"
    assert res.json()["service"] == "warehouse_service"
    assert res.json()["database"] == "connected"


@pytest.mark.django_db
def test_api_health_check_endpoint():
    client = APIClient()
    res = client.get("/api/health/")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["status"] == "ok"
