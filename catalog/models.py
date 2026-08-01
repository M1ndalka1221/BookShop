from django.db import models
from django.conf import settings

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Name")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="URL Slug")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"


class Book(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="books", verbose_name="Category")
    title = models.CharField(max_length=100, verbose_name="Title")
    author = models.CharField(max_length=100, verbose_name="Author")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Price")
    description = models.TextField(verbose_name="Description")
    stock = models.PositiveIntegerField(default=0, verbose_name="Stock")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Book"
        verbose_name_plural = "Books"


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    paid = models.BooleanField(default=False, verbose_name="Is Paid")
    stripe_id = models.CharField(max_length=250, blank=True, verbose_name="Stripe Payment ID")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    book = models.ForeignKey(Book, related_name='order_items', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Price")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantity")

    def __str__(self):
        return str(self.id)

    def get_cost(self):
        return self.price * self.quantity
