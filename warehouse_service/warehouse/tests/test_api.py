import pytest
from rest_framework.test import APIClient
from rest_framework import status
from users.models import CustomUser
from warehouse.models import Warehouse, WarehouseItem


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def service_user(db):
    return CustomUser.objects.create_user(
        username="bookshop_svc",
        password="svc_password_123",
        role=CustomUser.Role.SERVICE_ACCOUNT,
    )


@pytest.fixture
def manager_user(db):
    return CustomUser.objects.create_user(
        username="manager_boss",
        password="manager_password_123",
        role=CustomUser.Role.WAREHOUSE_MANAGER,
    )


@pytest.fixture
def warehouse_fixture(db):
    return Warehouse.objects.create(
        name="Main Storage",
        code="WH-01",
        location_details="Floor 1",
    )


@pytest.fixture
def items_fixture(db, warehouse_fixture):
    item1 = WarehouseItem.objects.create(
        warehouse=warehouse_fixture,
        book_id=1,
        sku="BK-001",
        title="Python Deep Dive",
        available_stock=10,
        reserved_stock=0,
        min_threshold=3,
    )
    item2 = WarehouseItem.objects.create(
        warehouse=warehouse_fixture,
        book_id=2,
        sku="BK-002",
        title="Distributed Systems",
        available_stock=5,
        reserved_stock=0,
        min_threshold=2,
    )
    return item1, item2


@pytest.mark.django_db
def test_jwt_authentication_endpoints(api_client, service_user):
    # Obtain token pair
    res = api_client.post(
        "/api/token/",
        {"username": "bookshop_svc", "password": "svc_password_123"},
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK
    assert "access" in res.data
    assert "refresh" in res.data
    access_token = res.data["access"]
    refresh_token = res.data["refresh"]

    # Verify token
    res_verify = api_client.post(
        "/api/token/verify/", {"token": access_token}, format="json"
    )
    assert res_verify.status_code == status.HTTP_200_OK

    # Refresh token
    res_refresh = api_client.post(
        "/api/token/refresh/", {"refresh": refresh_token}, format="json"
    )
    assert res_refresh.status_code == status.HTTP_200_OK
    assert "access" in res_refresh.data

    # Invalid credentials
    res_bad = api_client.post(
        "/api/token/",
        {"username": "bookshop_svc", "password": "wrong_password"},
        format="json",
    )
    assert res_bad.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_openapi_swagger_docs(api_client):
    res_schema = api_client.get("/api/schema/")
    assert res_schema.status_code == status.HTTP_200_OK

    res_docs = api_client.get("/api/docs/")
    assert res_docs.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_stock_reservation_flow(api_client, service_user, items_fixture):
    item1, item2 = items_fixture

    # Unauthenticated call rejected
    payload = {
        "order_id": 100,
        "items": [{"book_id": 1, "quantity": 3}, {"book_id": 2, "quantity": 2}],
    }
    res_unauth = api_client.post("/api/inventory/reserve/", payload, format="json")
    assert res_unauth.status_code == status.HTTP_401_UNAUTHORIZED

    # Authenticate as service account
    api_client.force_authenticate(user=service_user)

    # Successful reservation
    res = api_client.post("/api/inventory/reserve/", payload, format="json")
    assert res.status_code == status.HTTP_200_OK
    assert res.data["status"] == "RESERVED"
    assert len(res.data["reservations"]) == 2

    # Verify model changes
    item1.refresh_from_db()
    item2.refresh_from_db()
    assert item1.available_stock == 7
    assert item1.reserved_stock == 3
    assert item2.available_stock == 3
    assert item2.reserved_stock == 2

    # Stock check endpoint
    res_stock = api_client.get("/api/inventory/items/1/stock/")
    assert res_stock.status_code == status.HTTP_200_OK
    assert res_stock.data["available_stock"] == 7
    assert res_stock.data["reserved_stock"] == 3

    # Confirm sale
    res_confirm = api_client.post(
        "/api/inventory/confirm-sale/", {"order_id": 100}, format="json"
    )
    assert res_confirm.status_code == status.HTTP_200_OK
    assert res_confirm.data["confirmed_reservations"] == 2

    item1.refresh_from_db()
    assert item1.available_stock == 7
    assert item1.reserved_stock == 0


@pytest.mark.django_db
def test_stock_reservation_conflict_insufficient_stock(
    api_client, service_user, items_fixture
):
    item1, item2 = items_fixture
    api_client.force_authenticate(user=service_user)

    # Request more than available
    payload = {
        "order_id": 101,
        "items": [{"book_id": 1, "quantity": 20}],
    }
    res = api_client.post("/api/inventory/reserve/", payload, format="json")
    assert res.status_code == status.HTTP_409_CONFLICT
    assert bool(res.data["detail"]["error"]) is True
    assert str(res.data["detail"]["code"]) == "INSUFFICIENT_STOCK"

    # Stock was not modified
    item1.refresh_from_db()
    assert item1.available_stock == 10
    assert item1.reserved_stock == 0


@pytest.mark.django_db
def test_stock_release_flow(api_client, service_user, items_fixture):
    item1, _ = items_fixture
    api_client.force_authenticate(user=service_user)

    # Reserve
    api_client.post(
        "/api/inventory/reserve/",
        {"order_id": 102, "items": [{"book_id": 1, "quantity": 4}]},
        format="json",
    )
    item1.refresh_from_db()
    assert item1.available_stock == 6
    assert item1.reserved_stock == 4

    # Release
    res_rel = api_client.post(
        "/api/inventory/release/", {"order_id": 102}, format="json"
    )
    assert res_rel.status_code == status.HTTP_200_OK
    assert res_rel.data["released_reservations"] == 1

    item1.refresh_from_db()
    assert item1.available_stock == 10
    assert item1.reserved_stock == 0


@pytest.mark.django_db
def test_restock_permissions_and_operation(
    api_client, service_user, manager_user, items_fixture
):
    item1, _ = items_fixture

    # Service user cannot restock (Manager only)
    api_client.force_authenticate(user=service_user)
    res_forbidden = api_client.post(
        "/api/inventory/restock/",
        {"book_id": 1, "quantity": 50, "reference_id": "BATCH-01"},
        format="json",
    )
    assert res_forbidden.status_code == status.HTTP_403_FORBIDDEN

    # Manager restocks successfully
    api_client.force_authenticate(user=manager_user)
    res = api_client.post(
        "/api/inventory/restock/",
        {"book_id": 1, "quantity": 50, "reference_id": "BATCH-01"},
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.data["item"]["available_stock"] == 60

    item1.refresh_from_db()
    assert item1.available_stock == 60


@pytest.mark.django_db
def test_item_not_found_handling(api_client, service_user):
    api_client.force_authenticate(user=service_user)
    res = api_client.get("/api/inventory/items/99999/stock/")
    assert res.status_code == status.HTTP_404_NOT_FOUND
    assert res.data["detail"]["code"] == "ITEM_NOT_FOUND"
