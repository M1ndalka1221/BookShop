import json
import pytest
from unittest.mock import patch
from decimal import Decimal
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
import stripe

from catalog.models import Book, Category, Order, OrderItem
from catalog.tests.conftest import BookFactory, CategoryFactory, OrderFactory

User = get_user_model()


@pytest.mark.django_db
@patch('stripe.checkout.Session.create')
@patch('catalog.views.send_mail')
def test_full_checkout_flow(mock_send_mail, mock_stripe_create, client, user, book):
    mock_stripe_create.return_value.id = 'cs_test_mock_123'
    mock_stripe_create.return_value.url = 'https://checkout.stripe.com/mock'
    client.force_login(user)

    # 1. Add book to cart
    client.get(reverse('catalog:cart_add', kwargs={'book_id': book.id}))

    # 2. Inspect cart
    cart_response = client.get(reverse('catalog:cart_detail'))
    assert cart_response.status_code == 200
    assert book.title in str(cart_response.content)

    # 3. Checkout
    checkout_response = client.post(reverse('catalog:checkout'))
    assert checkout_response.status_code == 303
    assert checkout_response.url == 'https://checkout.stripe.com/mock'

    # 4. Verify DB state & Email
    order = Order.objects.get(user=user)
    assert order.stripe_id == 'cs_test_mock_123'
    assert order.items.count() == 1
    book.refresh_from_db()
    assert book.stock == 9
    mock_send_mail.assert_called_once()


@pytest.mark.django_db
def test_checkout_empty_cart(client, user):
    client.force_login(user)
    response = client.post(reverse('catalog:checkout'), follow=True)
    assert response.status_code == 200
    assert Order.objects.filter(user=user).count() == 0


@pytest.mark.django_db
def test_user_registration_and_login_flow(client):
    reg_url = reverse('register')
    reg_response = client.post(reg_url, {
        'username': 'integration_user',
        'email': 'integration@example.com',
        'password1': 'StrongPass123!',
        'password2': 'StrongPass123!',
    })
    assert reg_response.status_code == 302
    assert User.objects.filter(username='integration_user').exists()

    login_url = reverse('login')
    login_response = client.post(login_url, {
        'username': 'integration_user',
        'password': 'StrongPass123!',
    })
    assert login_response.status_code == 302


@pytest.mark.django_db
def test_catalog_browse_search_and_detail_flow(client, book):
    list_url = reverse('catalog:book_list')
    list_response = client.get(list_url)
    assert list_response.status_code == 200
    assert book.title in str(list_response.content)

    search_response = client.get(list_url, {'q': book.author})
    assert search_response.status_code == 200
    assert book.author in str(search_response.content)

    detail_url = reverse('catalog:book_detail', kwargs={'pk': book.pk})
    detail_response = client.get(detail_url)
    assert detail_response.status_code == 200
    assert book.title in str(detail_response.content)


@pytest.mark.django_db
def test_cart_add_quantity_and_total_calculation_flow(client, user):
    client.force_login(user)
    book1 = BookFactory(price="10.00", stock=5)
    book2 = BookFactory(price="20.00", stock=5)

    client.get(reverse('catalog:cart_add', kwargs={'book_id': book1.id}))
    client.get(reverse('catalog:cart_add', kwargs={'book_id': book1.id}))
    client.get(reverse('catalog:cart_add', kwargs={'book_id': book2.id}))

    cart_response = client.get(reverse('catalog:cart_detail'))
    assert cart_response.status_code == 200
    cart = cart_response.context['cart']
    assert len(cart) == 3
    assert cart.get_total_price() == Decimal("40.00")


@pytest.mark.django_db
def test_cart_remove_and_clear_flow(client, user):
    client.force_login(user)
    book = BookFactory(stock=5)

    client.get(reverse('catalog:cart_add', kwargs={'book_id': book.id}))
    cart_response = client.get(reverse('catalog:cart_detail'))
    cart = cart_response.context['cart']
    assert len(cart) == 1

    cart.clear()
    assert len(cart) == 0


@pytest.mark.django_db
def test_out_of_stock_item_cannot_be_added_flow(client, user):
    client.force_login(user)
    out_of_stock_book = BookFactory(stock=0)

    response = client.get(reverse('catalog:cart_add', kwargs={'book_id': out_of_stock_book.id}), follow=True)
    assert response.status_code == 200
    assert "currently out of stock" in str(response.content)


@pytest.mark.django_db
def test_admin_book_creation_and_update_flow(client, user, category):
    add_perm = Permission.objects.get(codename='add_book')
    change_perm = Permission.objects.get(codename='change_book')
    user.user_permissions.add(add_perm, change_perm)
    client.force_login(user)

    create_url = reverse('catalog:book_create')
    create_res = client.post(create_url, {
        'category': category.id,
        'title': 'New Integration Book',
        'author': 'Integration Author',
        'price': '25.00',
        'description': 'Integration Description',
        'stock': 15,
    })
    assert create_res.status_code == 302
    created_book = Book.objects.get(title='New Integration Book')

    update_url = reverse('catalog:book_update', kwargs={'pk': created_book.pk})
    update_res = client.post(update_url, {
        'category': category.id,
        'title': 'Updated Integration Book',
        'author': 'Integration Author',
        'price': '30.00',
        'description': 'Integration Description',
        'stock': 20,
    })
    assert update_res.status_code == 302
    created_book.refresh_from_db()
    assert created_book.title == 'Updated Integration Book'
    assert created_book.price == Decimal('30.00')


@pytest.mark.django_db
def test_admin_book_deletion_flow(client, user, book):
    delete_perm = Permission.objects.get(codename='delete_book')
    user.user_permissions.add(delete_perm)
    client.force_login(user)

    delete_url = reverse('catalog:book_delete', kwargs={'pk': book.pk})
    delete_res = client.post(delete_url)
    assert delete_res.status_code == 302
    assert not Book.objects.filter(pk=book.pk).exists()


@pytest.mark.django_db
def test_unauthorized_user_permission_denied_flow(client, user, book):
    client.force_login(user)
    create_url = reverse('catalog:book_create')
    response = client.get(create_url, follow=True)
    assert response.status_code == 200
    assert "do not have permission" in str(response.content)


@pytest.mark.django_db
@patch('stripe.checkout.Session.create')
def test_stripe_error_handling_flow(mock_stripe, client, user, book):
    mock_stripe.side_effect = stripe.error.StripeError("Card Declined")
    client.force_login(user)

    client.get(reverse('catalog:cart_add', kwargs={'book_id': book.id}))
    response = client.post(reverse('catalog:checkout'), follow=True)

    assert response.status_code == 200
    assert "Payment error: Card Declined" in str(response.content)


@pytest.mark.django_db
def test_insufficient_stock_at_checkout_flow(client, user):
    client.force_login(user)
    limited_book = BookFactory(stock=1)

    client.get(reverse('catalog:cart_add', kwargs={'book_id': limited_book.id}))

    limited_book.stock = 0
    limited_book.save()

    response = client.post(reverse('catalog:checkout'), follow=True)
    assert response.status_code == 200
    assert "does not have enough stock available" in str(response.content)
    assert Order.objects.filter(user=user).count() == 0


@pytest.mark.django_db
def test_async_views_integration_flow(client, book, order):
    res1 = client.get(reverse('catalog:async_book_count'))
    assert res1.status_code == 200
    assert json.loads(res1.content)['total_books'] >= 1

    res2 = client.get(reverse('catalog:async_categories_list'))
    assert res2.status_code == 200
    assert 'categories' in json.loads(res2.content)

    res3 = client.get(reverse('catalog:async_order_status', kwargs={'order_id': order.id}))
    assert res3.status_code == 200
    assert json.loads(res3.content)['status'] == 'Pending'


@pytest.mark.django_db
def test_language_switch_integration_flow(client):
    url = reverse('catalog:book_list')
    res_en = client.get(url, HTTP_ACCEPT_LANGUAGE='en')
    assert res_en.status_code == 200

    res_uk = client.get(url, HTTP_ACCEPT_LANGUAGE='uk')
    assert res_uk.status_code == 200


@pytest.mark.django_db
def test_cart_session_persistence_flow(client, user, book):
    client.force_login(user)
    client.get(reverse('catalog:cart_add', kwargs={'book_id': book.id}))

    res1 = client.get(reverse('catalog:cart_detail'))
    assert book.title in str(res1.content)

    res2 = client.get(reverse('catalog:cart_detail'))
    assert book.title in str(res2.content)