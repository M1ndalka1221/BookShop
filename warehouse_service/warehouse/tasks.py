import logging
from celery import shared_task
from django.utils import timezone
from django.db.models import F
from .models import StockReservation, WarehouseItem
from .services import release_stock, restock_item

logger = logging.getLogger("warehouse")


@shared_task(name="warehouse.tasks.release_expired_reservations")
def release_expired_reservations():
    """
    Scheduled task that finds pending reservations past their expiration
    and returns stock to the available pool.
    """
    now = timezone.now()
    expired_reservations = list(
        StockReservation.objects.filter(
            status=StockReservation.Status.PENDING, expires_at__lt=now
        ).values_list("id", flat=True)
    )

    if not expired_reservations:
        logger.info("No expired reservations found.")
        return 0

    logger.info("Releasing %s expired reservations: %s", len(expired_reservations), expired_reservations)
    count = release_stock(
        reservation_ids=expired_reservations,
        reason="Auto-released: reservation expired without payment",
    )
    return count


@shared_task(name="warehouse.tasks.check_low_stock_alerts")
def check_low_stock_alerts():
    """
    Scheduled task scanning for items where available_stock <= min_threshold.
    Generates structured alerts for warehouse managers.
    """
    low_stock_items = WarehouseItem.objects.filter(available_stock__lte=F("min_threshold"))

    alerts = []
    for item in low_stock_items:
        alert = {
            "book_id": item.book_id,
            "sku": item.sku,
            "title": item.title,
            "available_stock": item.available_stock,
            "min_threshold": item.min_threshold,
        }
        alerts.append(alert)
        logger.warning(
            "LOW STOCK ALERT: Item '%s' (SKU: %s, Book ID: %s) has %s available (threshold: %s)",
            item.title,
            item.sku,
            item.book_id,
            item.available_stock,
            item.min_threshold,
        )

    logger.info("Completed low stock check. Found %s items below threshold.", len(alerts))
    return alerts


@shared_task(name="warehouse.tasks.process_bulk_restock")
def process_bulk_restock(items_data: list, user_id=None):
    """
    Background worker task to process heavy restock payloads asynchronously.
    """
    from users.models import CustomUser

    user = CustomUser.objects.filter(id=user_id).first() if user_id else None
    processed = []

    for entry in items_data:
        book_id = entry.get("book_id")
        qty = entry.get("quantity", 0)
        ref = entry.get("reference_id", "BULK_RESTOCK")
        notes = entry.get("notes", "Asynchronous bulk restock")

        if book_id and qty > 0:
            try:
                restock_item(
                    book_id=book_id,
                    quantity=qty,
                    reference_id=ref,
                    notes=notes,
                    performed_by=user,
                )
                processed.append({"book_id": book_id, "quantity": qty})
            except Exception as e:
                logger.warning("Failed to restock item for book ID %s: %s", book_id, str(e))

    logger.info("Processed bulk restock for %s items.", len(processed))
    return processed
