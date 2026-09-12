from datetime import timedelta
from django.utils import timezone
import pytest
from warehouse.models import (
    Warehouse,
    WarehouseItem,
    StockReservation,
    StockTransaction,
)
from users.models import CustomUser


@pytest.mark.django_db
def test_warehouse_models():
    wh = Warehouse.objects.create(
        name="Central Depot",
        code="WH-CENTRAL",
        location_details="Building A",
    )
    assert str(wh) == "Central Depot (WH-CENTRAL)"

    item = WarehouseItem.objects.create(
        warehouse=wh,
        book_id=101,
        sku="BOOK-101",
        title="Refactoring Patterns",
        available_stock=10,
        reserved_stock=2,
        min_threshold=5,
    )
    assert item.total_stock == 12
    assert item.is_low_stock is False
    assert "Refactoring Patterns" in str(item)

    # Test is_low_stock flag
    item.available_stock = 4
    item.save()
    assert item.is_low_stock is True

    # Test StockReservation
    res = StockReservation.objects.create(
        item=item,
        order_id=505,
        quantity=2,
        expires_at=timezone.now() + timedelta(minutes=15),
    )
    assert res.status == StockReservation.Status.PENDING
    assert f"Order #505" in str(res)

    # Test StockTransaction
    user = CustomUser.objects.create_user(username="test_audit", password="password")
    tx = StockTransaction.objects.create(
        item=item,
        transaction_type=StockTransaction.TransactionType.RESTOCK,
        quantity_change=20,
        available_after=24,
        reference_id="PO-999",
        performed_by=user,
    )
    assert tx.quantity_change == 20
    assert "RESTOCK 20" in str(tx)
