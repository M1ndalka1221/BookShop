import time
import logging
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse

from users.permissions import IsWarehouseManager, IsServiceAccountOrStaff
from .models import WarehouseItem, StockTransaction, Warehouse
from .serializers import (
    WarehouseSerializer,
    WarehouseItemSerializer,
    StockTransactionSerializer,
    StockReservationSerializer,
    ReserveStockRequestSerializer,
    ConfirmSaleRequestSerializer,
    ReleaseStockRequestSerializer,
    RestockRequestSerializer,
)
from .services import (
    reserve_stock,
    confirm_sale,
    release_stock,
    restock_item,
    ItemNotFoundException,
)

logger = logging.getLogger("warehouse.interservice")


class BaseAPIView(APIView):
    """
    Base Class-Based View providing latency metrics, request logging, and error tracing.
    """

    def initial(self, request, *args, **kwargs):
        self._start_time = time.perf_counter()
        super().initial(request, *args, **kwargs)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if hasattr(self, "_start_time"):
            duration_ms = (time.perf_counter() - self._start_time) * 1000
            response["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
            user_str = str(request.user) if request.user.is_authenticated else "Anonymous"
            logger.info(
                "%s %s - User: %s - Status: %s - Latency: %.2fms",
                request.method,
                request.path,
                user_str,
                response.status_code,
                duration_ms,
            )
        return response


class BaseInventoryAPIView(BaseAPIView):
    """
    Base Class-Based View for inventory endpoints requiring service or staff authentication.
    """

    permission_classes = [IsServiceAccountOrStaff]


class ReserveStockAPIView(BaseInventoryAPIView):
    """
    Atomic stock reservation endpoint called by Project A (BookShop) during order checkout.
    """

    @extend_schema(
        request=ReserveStockRequestSerializer,
        responses={
            200: OpenApiResponse(description="Stock reserved successfully"),
            409: OpenApiResponse(description="Insufficient stock conflict"),
            404: OpenApiResponse(description="Book item not found in warehouse"),
        },
        summary="Reserve stock for pending order",
    )
    def post(self, request, *args, **kwargs):
        serializer = ReserveStockRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        reservations = reserve_stock(
            order_id=data["order_id"],
            items=data["items"],
            expires_in_minutes=data.get("expires_in_minutes", 15),
            performed_by=request.user,
        )

        return Response(
            {
                "status": "RESERVED",
                "order_id": data["order_id"],
                "reservations": StockReservationSerializer(reservations, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


class ConfirmSaleAPIView(BaseInventoryAPIView):
    """
    Confirms stock reservation when payment succeeds in Project A.
    """

    @extend_schema(
        request=ConfirmSaleRequestSerializer,
        responses={200: OpenApiResponse(description="Stock confirmed successfully")},
        summary="Confirm stock reservations after payment",
    )
    def post(self, request, *args, **kwargs):
        serializer = ConfirmSaleRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        count = confirm_sale(
            order_id=data.get("order_id"),
            reservation_ids=data.get("reservation_ids"),
            performed_by=request.user,
        )

        return Response(
            {
                "status": "CONFIRMED",
                "confirmed_reservations": count,
            },
            status=status.HTTP_200_OK,
        )


class ReleaseStockAPIView(BaseInventoryAPIView):
    """
    Releases stock reservations when checkout is cancelled or payment fails in Project A.
    """

    @extend_schema(
        request=ReleaseStockRequestSerializer,
        responses={200: OpenApiResponse(description="Stock released successfully")},
        summary="Release stock reservations back to available pool",
    )
    def post(self, request, *args, **kwargs):
        serializer = ReleaseStockRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        count = release_stock(
            order_id=data.get("order_id"),
            reservation_ids=data.get("reservation_ids"),
            performed_by=request.user,
        )

        return Response(
            {
                "status": "RELEASED",
                "released_reservations": count,
            },
            status=status.HTTP_200_OK,
        )


class RestockItemAPIView(BaseAPIView):
    """
    Allows Warehouse Managers to restock inventory with full audit tracking.
    """

    permission_classes = [IsWarehouseManager]

    @extend_schema(
        request=RestockRequestSerializer,
        responses={200: WarehouseItemSerializer},
        summary="Restock an item (Manager only)",
    )
    def post(self, request, *args, **kwargs):
        serializer = RestockRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        item = restock_item(
            book_id=data["book_id"],
            quantity=data["quantity"],
            reference_id=data.get("reference_id", ""),
            notes=data.get("notes", ""),
            performed_by=request.user,
        )

        return Response(
            {
                "status": "RESTOCKED",
                "item": WarehouseItemSerializer(item).data,
            },
            status=status.HTTP_200_OK,
        )


class ItemStockCheckAPIView(BaseInventoryAPIView):
    """
    Fast, cached stock check endpoint for a specific book ID.
    """

    @extend_schema(
        responses={200: OpenApiResponse(description="Item stock levels")},
        summary="Check stock level for book ID",
    )
    def get(self, request, book_id: int, *args, **kwargs):
        cache_key = f"wh:stock:{book_id}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)

        try:
            item = WarehouseItem.objects.get(book_id=book_id)
        except WarehouseItem.DoesNotExist:
            raise ItemNotFoundException(book_id)

        data = {
            "book_id": item.book_id,
            "sku": item.sku,
            "title": item.title,
            "available_stock": item.available_stock,
            "reserved_stock": item.reserved_stock,
            "total_stock": item.total_stock,
            "is_low_stock": item.is_low_stock,
        }
        cache.set(cache_key, data, timeout=300)
        return Response(data, status=status.HTTP_200_OK)


class WarehouseViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for warehouses.
    """

    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [IsWarehouseManager]


class WarehouseItemViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for warehouse items.
    """

    queryset = WarehouseItem.objects.select_related("warehouse").all()
    serializer_class = WarehouseItemSerializer
    permission_classes = [IsServiceAccountOrStaff]
    filterset_fields = ("book_id", "sku", "warehouse")
    search_fields = ("title", "sku")


class StockTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Audit log trail of stock movements.
    """

    queryset = StockTransaction.objects.select_related("item", "performed_by").all()
    serializer_class = StockTransactionSerializer
    permission_classes = [IsWarehouseManager]
    filterset_fields = ("transaction_type", "item", "reference_id")
