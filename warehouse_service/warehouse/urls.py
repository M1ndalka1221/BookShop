from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    WarehouseViewSet,
    WarehouseItemViewSet,
    StockTransactionViewSet,
    ReserveStockAPIView,
    ConfirmSaleAPIView,
    ReleaseStockAPIView,
    RestockItemAPIView,
    ItemStockCheckAPIView,
)

app_name = "warehouse"

router = DefaultRouter()
router.register("warehouses", WarehouseViewSet, basename="warehouse")
router.register("items", WarehouseItemViewSet, basename="warehouse_item")
router.register("transactions", StockTransactionViewSet, basename="stock_transaction")

urlpatterns = [
    # Dedicated operational endpoints for inter-service communication
    path("reserve/", ReserveStockAPIView.as_view(), name="reserve_stock"),
    path("confirm-sale/", ConfirmSaleAPIView.as_view(), name="confirm_sale"),
    path("release/", ReleaseStockAPIView.as_view(), name="release_stock"),
    path("restock/", RestockItemAPIView.as_view(), name="restock_item"),
    path(
        "items/<int:book_id>/stock/",
        ItemStockCheckAPIView.as_view(),
        name="item_stock_check",
    ),
    # Standard CRUD router endpoints
    path("", include(router.urls)),
]
