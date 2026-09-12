from django.contrib import admin
from .models import Warehouse, WarehouseItem, StockReservation, StockTransaction


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    search_fields = ("name", "code")


@admin.register(WarehouseItem)
class WarehouseItemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "sku",
        "book_id",
        "available_stock",
        "reserved_stock",
        "total_stock",
        "min_threshold",
        "is_low_stock",
    )
    list_filter = ("warehouse",)
    search_fields = ("title", "sku", "book_id")


@admin.register(StockReservation)
class StockReservationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "item",
        "order_id",
        "quantity",
        "status",
        "created_at",
        "expires_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("order_id", "item__title", "item__sku")


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "item",
        "transaction_type",
        "quantity_change",
        "available_after",
        "reference_id",
        "performed_by",
        "created_at",
    )
    list_filter = ("transaction_type", "created_at")
    search_fields = ("reference_id", "item__title", "item__sku")
