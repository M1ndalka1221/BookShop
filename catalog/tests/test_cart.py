import pytest
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from catalog.cart import Cart
from .conftest import BookFactory


@pytest.fixture
def mock_request():
    request = RequestFactory().get('/')
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    return request


@pytest.mark.django_db
def test_cart_add(mock_request):
    cart = Cart(mock_request)
    book = BookFactory(price="20.00")

    cart.add(book=book, quantity=2)
    assert len(cart) == 2
    assert cart.get_total_price() == 40.00


@pytest.mark.django_db
def test_cart_remove(mock_request):
    cart = Cart(mock_request)
    book = BookFactory()

    cart.add(book=book, quantity=1)
    cart.remove(book)
    assert len(cart) == 0


@pytest.mark.django_db
def test_cart_clear(mock_request):
    cart = Cart(mock_request)
    book = BookFactory()

    cart.add(book=book)
    cart.clear()
    assert len(cart) == 0


@pytest.mark.django_db
def test_cart_iter(mock_request):
    cart = Cart(mock_request)
    book = BookFactory(price="10.00")
    cart.add(book=book, quantity=1)

    for item in cart:
        assert item['book'] == book
        assert item['total_price'] == 10.00