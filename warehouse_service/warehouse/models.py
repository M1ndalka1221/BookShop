import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Warehouse(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Warehouse Name"))
    code = models.CharField(
        max_length=20, unique=True, verbose_name=_("Warehouse Code")
    )
    location_details = models.CharField(
        max_length=255, blank=True, verbose_name=_("Location Details")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))

    class Meta:
        verbose_name = _("Warehouse")
        verbose_name_plural = _("Warehouses")

    def __str__(self):
        return f"{self.name} ({self.code})"


class WarehouseItem(models.Model):
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("Warehouse"),
    )
    book_id = models.PositiveIntegerField(
        db_index=True, verbose_name=_("BookShop Book ID")
    )
    sku = models.CharField(max_length=50, unique=True, verbose_name=_("SKU"))
    title = models.CharField(max_length=255, verbose_name=_("Item Title"))
    available_stock = models.PositiveIntegerField(
        default=0, verbose_name=_("Available Stock")
    )
    reserved_stock = models.PositiveIntegerField(
        default=0, verbose_name=_("Reserved Stock")
    )
    min_threshold = models.PositiveIntegerField(
        default=5, verbose_name=_("Minimum Restock Threshold")
    )
    shelf_location = models.CharField(
        max_length=50, blank=True, verbose_name=_("Shelf Location")
    )

    class Meta:
        verbose_name = _("Warehouse Item")
        verbose_name_plural = _("Warehouse Items")
        ordering = ["id"]

    @property
    def total_stock(self):
        return self.available_stock + self.reserved_stock

    @property
    def is_low_stock(self):
        return self.available_stock <= self.min_threshold

    def __str__(self):
        return f"{self.title} [SKU: {self.sku}] - Avail: {self.available_stock}"


class StockReservation(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        CONFIRMED = "CONFIRMED", _("Confirmed")
        RELEASED = "RELEASED", _("Released")
        EXPIRED = "EXPIRED", _("Expired")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(
        WarehouseItem,
        on_delete=models.CASCADE,
        related_name="reservations",
        verbose_name=_("Item"),
    )
    order_id = models.PositiveIntegerField(
        db_index=True, verbose_name=_("BookShop Order ID")
    )
    quantity = models.PositiveIntegerField(verbose_name=_("Quantity"))
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("Status"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    expires_at = models.DateTimeField(verbose_name=_("Expires At"))

    class Meta:
        verbose_name = _("Stock Reservation")
        verbose_name_plural = _("Stock Reservations")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Reservation {self.id} (Order #{self.order_id}, Qty: {self.quantity}) - {self.status}"


class StockTransaction(models.Model):
    class TransactionType(models.TextChoices):
        RESTOCK = "RESTOCK", _("Restock")
        RESERVE = "RESERVE", _("Reserve")
        CONFIRM_SALE = "CONFIRM_SALE", _("Confirm Sale")
        RELEASE = "RELEASE", _("Release")
        ADJUSTMENT = "ADJUSTMENT", _("Manual Adjustment")

    item = models.ForeignKey(
        WarehouseItem,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name=_("Item"),
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        verbose_name=_("Transaction Type"),
    )
    quantity_change = models.IntegerField(verbose_name=_("Quantity Change"))
    available_after = models.PositiveIntegerField(
        verbose_name=_("Available Stock After")
    )
    reference_id = models.CharField(
        max_length=100, blank=True, verbose_name=_("Reference ID")
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="stock_transactions",
        verbose_name=_("Performed By"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    notes = models.TextField(blank=True, verbose_name=_("Notes"))

    class Meta:
        verbose_name = _("Stock Transaction")
        verbose_name_plural = _("Stock Transactions")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.transaction_type} {self.quantity_change} on {self.item.sku} (Ref: {self.reference_id})"
