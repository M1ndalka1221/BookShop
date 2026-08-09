import pytest
import json
from django.urls import reverse
from .conftest import BookFactory, CategoryFactory, OrderFactory


@pytest.mark.django_db
def test_async_book_count(client):
    BookFactory.create_batch(3)
    url = reverse('catalog:async_book_count')
    response = client.get(url)

    assert response.status_code == 200
    data = json.loads(response.content)
    assert data['total_books'] == 3


@pytest.mark.django_db
def test_async_categories_list(client):
    CategoryFactory(name="Fantasy", slug="fantasy")
    url = reverse('catalog:async_categories_list')
    response = client.get(url)

    assert response.status_code == 200
    data = json.loads(response.content)
    assert data['categories'][0]['name'] == "Fantasy"


@pytest.mark.django_db
def test_async_order_status(client, order):
    order.paid = True
    order.save()
    url = reverse('catalog:async_order_status', kwargs={'order_id': order.id})
    response = client.get(url)

    assert response.status_code == 200
    data = json.loads(response.content)
    assert data['status'] == 'Paid'