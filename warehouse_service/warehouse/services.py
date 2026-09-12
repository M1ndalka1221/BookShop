import logging
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from django.core.cache import cache
from rest_framework.exceptions import APIException
from rest_framework import status
from .models import WarehouseItem, StockReservation, StockTransaction

logger = logging.getLogger("warehouse.interservice")


class InsufficientStockException(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "INSUFFICIENT_STOCK"

    def __init__(self, item, requested, available):
        detail = {
            "error": True,
            "code": self.default_code,
            "message": f"Insufficient stock for book ID {item.book_id} ('{item.title}').",
            "book_id": item.book_id,
            "sku": item.sku,
            "requested": requested,
            "available": available,
        }
        super().__init__(detail)


class ItemNotFoundException(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = "ITEM_NOT_FOUND"

    def __init__(self, book_id):
        detail = {
            "error": True,
            "code": self.default_code,
            "message": f"Warehouse item for book ID {book_id} was not found.",
            "book_id": book_id,
        }
        super().__init__(detail)


def invalidate_item_cache(book_id: int):
    """
    Invalidates Redis stock cache for the given book ID.
    """
    cache_key = f"wh:stock:{book_id}"
    cache.delete(cache_key)


def reserve_stock(
    order_id: int, items: list, expires_in_minutes: int = 15, performed_by=None
):
    """
    Atomically reserves stock for a collection of items during checkout.
    Uses select_for_update() to prevent race conditions.
    """
    logger.info(
        "Initiating stock reservation for order #%s with %s items", order_id, len(items)
    )

    with transaction.atomic():
        book_ids = [it["book_id"] for it in items]
        warehouse_items = {
            wh_item.book_id: wh_item
            for wh_item in WarehouseItem.objects.select_for_update().filter(
                book_id__in=book_ids
            )
        }

        # Validate existence
        for it in items:
            b_id = it["book_id"]
            if b_id not in warehouse_items:
                logger.warning(
                    "Reservation failed: book ID %s not found in warehouse", b_id
                )
                raise ItemNotFoundException(b_id)

        # Validate stock levels
        for it in items:
            b_id = it["book_id"]
            qty = it["quantity"]
            wh_item = warehouse_items[b_id]
            if wh_item.available_stock < qty:
                logger.warning(
                    "Reservation conflict: book ID %s requested %s, available %s",
                    b_id,
                    qty,
                    wh_item.available_stock,
                )
                raise InsufficientStockException(wh_item, qty, wh_item.available_stock)

        # Apply stock deduction and reserve
        expires_at = timezone.now() + timedelta(minutes=expires_in_minutes)
        created_reservations = []

        for it in items:
            b_id = it["book_id"]
            qty = it["quantity"]
            wh_item = warehouse_items[b_id]

            wh_item.available_stock -= qty
            wh_item.reserved_stock += qty
            wh_item.save(update_fields=["available_stock", "reserved_stock"])

            reservation = StockReservation.objects.create(
                item=wh_item,
                order_id=order_id,
                quantity=qty,
                expires_at=expires_at,
                status=StockReservation.Status.PENDING,
            )
            created_reservations.append(reservation)

            StockTransaction.objects.create(
                item=wh_item,
                transaction_type=StockTransaction.TransactionType.RESERVE,
                quantity_change=-qty,
                available_after=wh_item.available_stock,
                reference_id=f"Order #{order_id}",
                performed_by=performed_by,
                notes=f"Reserved {qty} units for Order #{order_id}",
            )
            invalidate_item_cache(b_id)

        logger.info(
            "Successfully reserved stock for order #%s. Reservation IDs: %s",
            order_id,
            [str(r.id) for r in created_reservations],
        )
        return created_reservations


def confirm_sale(order_id: int = None, reservation_ids: list = None, performed_by=None):
    """
    Confirms sale for reservations after successful payment.
    Clears reserved_stock permanently.
    """
    with transaction.atomic():
        qs = StockReservation.objects.select_for_update().filter(
            status=StockReservation.Status.PENDING
        )
        if order_id:
            qs = qs.filter(order_id=order_id)
        elif reservation_ids:
            qs = qs.filter(id__in=reservation_ids)
        else:
            return 0

        reservations = list(qs)
        for res in reservations:
            item = res.item
            item.reserved_stock = max(0, item.reserved_stock - res.quantity)
            item.save(update_fields=["reserved_stock"])

            res.status = StockReservation.Status.CONFIRMED
            res.save(update_fields=["status"])

            StockTransaction.objects.create(
                item=item,
                transaction_type=StockTransaction.TransactionType.CONFIRM_SALE,
                quantity_change=0,
                available_after=item.available_stock,
                reference_id=f"Order #{res.order_id}",
                performed_by=performed_by,
                notes=f"Confirmed sale of {res.quantity} units for Order #{res.order_id}",
            )
            invalidate_item_cache(item.book_id)

        logger.info(
            "Confirmed %s reservations for order #%s", len(reservations), order_id
        )
        return len(reservations)


def release_stock(
    order_id: int = None,
    reservation_ids: list = None,
    performed_by=None,
    reason: str = "Payment failed or cancelled",
):
    """
    Releases pending reservations back to available_stock.
    """
    with transaction.atomic():
        qs = StockReservation.objects.select_for_update().filter(
            status=StockReservation.Status.PENDING
        )
        if order_id:
            qs = qs.filter(order_id=order_id)
        elif reservation_ids:
            qs = qs.filter(id__in=reservation_ids)
        else:
            return 0

        reservations = list(qs)
        for res in reservations:
            item = res.item
            item.available_stock += res.quantity
            item.reserved_stock = max(0, item.reserved_stock - res.quantity)
            item.save(update_fields=["available_stock", "reserved_stock"])

            res.status = StockReservation.Status.RELEASED
            res.save(update_fields=["status"])

            StockTransaction.objects.create(
                item=item,
                transaction_type=StockTransaction.TransactionType.RELEASE,
                quantity_change=res.quantity,
                available_after=item.available_stock,
                reference_id=f"Order #{res.order_id}",
                performed_by=performed_by,
                notes=reason,
            )
            invalidate_item_cache(item.book_id)

        logger.info(
            "Released %s reservations for order #%s (%s)",
            len(reservations),
            order_id,
            reason,
        )
        return len(reservations)


def restock_item(
    book_id: int,
    quantity: int,
    reference_id: str = "",
    notes: str = "",
    performed_by=None,
):
    """
    Adds available stock to an item and creates an audit transaction.
    """
    with transaction.atomic():
        try:
            item = WarehouseItem.objects.select_for_update().get(book_id=book_id)
        except WarehouseItem.DoesNotExist:
            raise ItemNotFoundException(book_id)

        item.available_stock += quantity
        item.save(update_fields=["available_stock"])

        StockTransaction.objects.create(
            item=item,
            transaction_type=StockTransaction.TransactionType.RESTOCK,
            quantity_change=quantity,
            available_after=item.available_stock,
            reference_id=reference_id,
            performed_by=performed_by,
            notes=notes,
        )
        invalidate_item_cache(book_id)
        logger.info(
            "Restocked %s units for book ID %s. New available: %s",
            quantity,
            book_id,
            item.available_stock,
        )
        return item
