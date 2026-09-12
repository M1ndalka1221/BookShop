from warehouse.serializers import (
    ReserveStockRequestSerializer,
    ConfirmSaleRequestSerializer,
    ReleaseStockRequestSerializer,
    RestockRequestSerializer,
)


def test_reserve_stock_serializer():
    # Valid payload
    data = {
        "order_id": 1,
        "items": [
            {"book_id": 10, "quantity": 2},
            {"book_id": 11, "quantity": 1},
        ],
        "expires_in_minutes": 20,
    }
    ser = ReserveStockRequestSerializer(data=data)
    assert ser.is_valid(), ser.errors

    # Invalid payload (empty items)
    bad_data = {"order_id": 1, "items": []}
    ser_bad = ReserveStockRequestSerializer(data=bad_data)
    assert not ser_bad.is_valid()
    assert "items" in ser_bad.errors

    # Invalid payload (negative quantity)
    bad_qty = {
        "order_id": 1,
        "items": [{"book_id": 10, "quantity": 0}],
    }
    ser_qty = ReserveStockRequestSerializer(data=bad_qty)
    assert not ser_qty.is_valid()


def test_confirm_and_release_serializers():
    # Valid with order_id
    ser_confirm = ConfirmSaleRequestSerializer(data={"order_id": 12})
    assert ser_confirm.is_valid()

    # Invalid without either order_id or reservation_ids
    ser_empty = ConfirmSaleRequestSerializer(data={})
    assert not ser_empty.is_valid()

    ser_release_empty = ReleaseStockRequestSerializer(data={})
    assert not ser_release_empty.is_valid()


def test_restock_serializer():
    data = {"book_id": 5, "quantity": 100, "reference_id": "BATCH-1"}
    ser = RestockRequestSerializer(data=data)
    assert ser.is_valid()
    assert ser.validated_data["quantity"] == 100
