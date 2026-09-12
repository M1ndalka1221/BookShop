from rest_framework import serializers
from .models import Warehouse, WarehouseItem, StockReservation, StockTransaction


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ("id", "name", "code", "location_details", "is_active")


class WarehouseItemSerializer(serializers.ModelSerializer):
    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True)
    total_stock = serializers.IntegerField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = WarehouseItem
        fields = (
            "id",
            "warehouse",
            "warehouse_code",
            "book_id",
            "sku",
            "title",
            "available_stock",
            "reserved_stock",
            "total_stock",
            "min_threshold",
            "is_low_stock",
            "shelf_location",
        )
        read_only_fields = ("id", "total_stock", "is_low_stock")


class StockReservationSerializer(serializers.ModelSerializer):
    item_title = serializers.CharField(source="item.title", read_only=True)
    item_sku = serializers.CharField(source="item.sku", read_only=True)

    class Meta:
        model = StockReservation
        fields = (
            "id",
            "item",
            "item_title",
            "item_sku",
            "order_id",
            "quantity",
            "status",
            "created_at",
            "expires_at",
        )
        read_only_fields = ("id", "created_at")


class StockTransactionSerializer(serializers.ModelSerializer):
    item_sku = serializers.CharField(source="item.sku", read_only=True)
    performed_by_username = serializers.CharField(
        source="performed_by.username", read_only=True
    )

    class Meta:
        model = StockTransaction
        fields = (
            "id",
            "item",
            "item_sku",
            "transaction_type",
            "quantity_change",
            "available_after",
            "reference_id",
            "performed_by",
            "performed_by_username",
            "created_at",
            "notes",
        )
        read_only_fields = ("id", "created_at")


class ReserveItemInputSerializer(serializers.Serializer):
    book_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)


class ReserveStockRequestSerializer(serializers.Serializer):
    order_id = serializers.IntegerField(min_value=1)
    items = ReserveItemInputSerializer(many=True, allow_empty=False)
    expires_in_minutes = serializers.IntegerField(min_value=1, max_value=60, default=15)


class ConfirmSaleRequestSerializer(serializers.Serializer):
    order_id = serializers.IntegerField(min_value=1, required=False)
    reservation_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, allow_empty=True
    )

    def validate(self, attrs):
        if not attrs.get("order_id") and not attrs.get("reservation_ids"):
            raise serializers.ValidationError(
                "Either order_id or reservation_ids must be provided."
            )
        return attrs


class ReleaseStockRequestSerializer(serializers.Serializer):
    order_id = serializers.IntegerField(min_value=1, required=False)
    reservation_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, allow_empty=True
    )

    def validate(self, attrs):
        if not attrs.get("order_id") and not attrs.get("reservation_ids"):
            raise serializers.ValidationError(
                "Either order_id or reservation_ids must be provided."
            )
        return attrs


class RestockRequestSerializer(serializers.Serializer):
    book_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)
    reference_id = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=""
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")
