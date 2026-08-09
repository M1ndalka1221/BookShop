from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Name"))
    slug = models.SlugField(max_length=100, unique=True, verbose_name=_("URL Slug"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")


class Book(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="books", verbose_name=_("Category"))
    title = models.CharField(max_length=100, verbose_name=_("Title"))
    author = models.CharField(max_length=100, verbose_name=_("Author"))
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Price"))
    description = models.TextField(verbose_name=_("Description"))
    stock = models.PositiveIntegerField(default=0, verbose_name=_("Stock"))

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['id']
        verbose_name = _("Book")
        verbose_name_plural = _("Books")


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    paid = models.BooleanField(default=False, verbose_name=_("Is Paid"))
    stripe_id = models.CharField(max_length=250, blank=True, verbose_name=_("Stripe Payment ID"))

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    book = models.ForeignKey(Book, related_name='order_items', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Price"))
    quantity = models.PositiveIntegerField(default=1, verbose_name=_("Quantity"))

    def __str__(self):
        return str(self.id)

    def get_cost(self):
        from decimal import Decimal
        return Decimal(self.price) * self.quantity
