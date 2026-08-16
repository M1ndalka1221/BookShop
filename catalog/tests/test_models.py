# Generated with AI, reviewed and modified
import pytest
from decimal import Decimal
from catalog.models import Category, Book, Order, OrderItem
from .conftest import CategoryFactory, BookFactory, OrderFactory, OrderItemFactory


@pytest.mark.django_db
def test_category_str():
    """Test string representation of Category model."""
    category = CategoryFactory(name="Sci-Fi")
    assert str(category) == "Sci-Fi"


@pytest.mark.django_db
def test_book_str():
    """Test string representation of Book model."""
    book = BookFactory(title="Dune")
    assert str(book) == "Dune"


@pytest.mark.django_db
def test_order_str(user):
    """Test string representation of Order model."""
    order = OrderFactory(user=user, id=5)
    assert str(order) == f"Order 5 by {user.username}"


@pytest.mark.django_db
def test_order_item_str():
    """Test string representation of OrderItem model."""
    item = OrderItemFactory(id=10)
    assert str(item) == "10"


@pytest.mark.django_db
def test_order_item_get_cost():
    """Test get_cost calculation on OrderItem model."""
    item = OrderItemFactory(price=Decimal("10.00"), quantity=3)
    assert item.get_cost() == Decimal("30.00")


@pytest.mark.django_db
def test_category_verbose_name_plural():
    """Test verbose_name_plural meta option on Category model."""
    assert str(Category._meta.verbose_name_plural) == "Categories"


@pytest.mark.django_db
def test_book_default_stock():
    """Test default stock value when creating a Book."""
    category = CategoryFactory()
    book = Book.objects.create(category=category, title="Test", author="Author", price=Decimal("15.00"))
    assert book.stock == 0


@pytest.mark.django_db
def test_order_default_unpaid(user):
    """Test default values for newly created Order."""
    order = Order.objects.create(user=user)
    assert order.paid is False
    assert order.stripe_id == ""


@pytest.mark.django_db
def test_book_ordering():
    """Test ordering meta setting for Book model."""
    assert Book._meta.ordering == ['id']


@pytest.mark.django_db
def test_order_ordering():
    """Test ordering meta setting for Order model."""
    assert Order._meta.ordering == ['-created_at']