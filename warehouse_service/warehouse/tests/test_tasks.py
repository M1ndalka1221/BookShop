from datetime import timedelta
from django.utils import timezone
import pytest
from warehouse.models import Warehouse, WarehouseItem, StockReservation
from warehouse.tasks import (
    release_expired_reservations,
    check_low_stock_alerts,
    process_bulk_restock,
)


@pytest.fixture
def sample_warehouse(db):
    return Warehouse.objects.create(name="Task Warehouse", code="WH-TSK")


@pytest.mark.django_db
def test_release_expired_reservations_task(sample_warehouse):
    item = WarehouseItem.objects.create(
        warehouse=sample_warehouse,
        book_id=55,
        sku="TSK-55",
        title="Async Python",
        available_stock=5,
        reserved_stock=5,
    )

    now = timezone.now()
    # Expired reservation
    res_expired = StockReservation.objects.create(
        item=item,
        order_id=901,
        quantity=3,
        status=StockReservation.Status.PENDING,
        expires_at=now - timedelta(minutes=5),
    )
    # Active reservation
    res_active = StockReservation.objects.create(
        item=item,
        order_id=902,
        quantity=2,
        status=StockReservation.Status.PENDING,
        expires_at=now + timedelta(minutes=10),
    )

    count = release_expired_reservations()
    assert count == 1

    item.refresh_from_db()
    res_expired.refresh_from_db()
    res_active.refresh_from_db()

    # Expired was released and added back to available
    assert item.available_stock == 8
    assert item.reserved_stock == 2
    assert res_expired.status == StockReservation.Status.RELEASED
    assert res_active.status == StockReservation.Status.PENDING

    # Running again finds 0 expired
    assert release_expired_reservations() == 0


@pytest.mark.django_db
def test_check_low_stock_alerts_task(sample_warehouse):
    item_low = WarehouseItem.objects.create(
        warehouse=sample_warehouse,
        book_id=60,
        sku="TSK-60",
        title="Low Stock Book",
        available_stock=2,
        min_threshold=5,
    )
    item_ok = WarehouseItem.objects.create(
        warehouse=sample_warehouse,
        book_id=61,
        sku="TSK-61",
        title="Well Stocked Book",
        available_stock=20,
        min_threshold=5,
    )

    alerts = check_low_stock_alerts()
    alert_book_ids = [a["book_id"] for a in alerts]

    assert item_low.book_id in alert_book_ids
    assert item_ok.book_id not in alert_book_ids


@pytest.mark.django_db
def test_process_bulk_restock_task(sample_warehouse):
    item = WarehouseItem.objects.create(
        warehouse=sample_warehouse,
        book_id=70,
        sku="TSK-70",
        title="Bulk Restock Book",
        available_stock=10,
    )

    data = [
        {"book_id": 70, "quantity": 15, "reference_id": "PO-TEST"},
        {"book_id": 999, "quantity": 10},  # Invalid, ignored or handled safely
    ]
    result = process_bulk_restock(data)
    assert len(result) == 1
    assert result[0]["book_id"] == 70

    item.refresh_from_db()
    assert item.available_stock == 25
