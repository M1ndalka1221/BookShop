import pytest
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework import status
from users.models import CustomUser
from warehouse.models import Warehouse, WarehouseItem
from warehouse.services import reserve_stock, restock_item


@pytest.mark.django_db
def test_stock_cache_lifecycle():
    client = APIClient()
    service_user = CustomUser.objects.create_user(
        username="cache_tester",
        password="password",
        role=CustomUser.Role.SERVICE_ACCOUNT,
    )
    client.force_authenticate(user=service_user)

    wh = Warehouse.objects.create(name="Cache WH", code="WH-CACHE")
    item = WarehouseItem.objects.create(
        warehouse=wh,
        book_id=88,
        sku="CACHE-88",
        title="Caching Guide",
        available_stock=50,
        reserved_stock=0,
    )

    cache_key = f"wh:stock:88"
    cache.delete(cache_key)
    assert cache.get(cache_key) is None

    # First GET populates the cache
    res1 = client.get(f"/api/inventory/items/{item.book_id}/stock/")
    assert res1.status_code == status.HTTP_200_OK
    assert res1.data["available_stock"] == 50

    cached_data = cache.get(cache_key)
    assert cached_data is not None
    assert cached_data["available_stock"] == 50

    # Mutating stock via reserve invalidates cache
    reserve_stock(order_id=999, items=[{"book_id": 88, "quantity": 10}])
    assert cache.get(cache_key) is None

    # Next GET repopulates with updated stock
    res2 = client.get(f"/api/inventory/items/{item.book_id}/stock/")
    assert res2.status_code == status.HTTP_200_OK
    assert res2.data["available_stock"] == 40
    assert cache.get(cache_key)["available_stock"] == 40

    # Restock invalidates cache
    restock_item(book_id=88, quantity=20)
    assert cache.get(cache_key) is None
