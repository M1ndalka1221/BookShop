import pytest
from catalog.models import Category, Book, Order, OrderItem
from .conftest import CategoryFactory, BookFactory, OrderFactory, OrderItemFactory

@pytest.mark.django_db
def test_category_str():
    category = CategoryFactory(name="Sci-Fi")
    assert str(category) == "Sci-Fi"

@pytest.mark.django_db
def test_book_str():
    book = BookFactory(title="Dune")
    assert str(book) == "Dune"

@pytest.mark.django_db
def test_order_str(user):
    order = OrderFactory(user=user, id=5)
    assert str(order) == f"Order 5 by {user.username}"

@pytest.mark.django_db
def test_order_item_str():
    item = OrderItemFactory(id=10)
    assert str(item) == "10"

@pytest.mark.django_db
def test_order_item_get_cost():
    item = OrderItemFactory(price="10.00", quantity=3)
    assert item.get_cost() == 30.00


@pytest.mark.django_db
def test_category_verbose_name_plural():
    assert str(Category._meta.verbose_name_plural) == "Categories"


@pytest.mark.django_db
def test_book_default_stock():
    category = CategoryFactory()
    book = Book.objects.create(category=category, title="Test", author="Author", price="15.00")
    assert book.stock == 0


@pytest.mark.django_db
def test_order_default_unpaid(user):
    order = Order.objects.create(user=user)
    assert order.paid is False
    assert order.stripe_id == ""