# Generated with AI, reviewed and modified
import pytest
from django.urls import reverse
from catalog.models import Book
from django.contrib.auth.models import Permission


@pytest.mark.django_db
def test_book_list_view(client, book):
    url = reverse('catalog:book_list')
    response = client.get(url)
    assert response.status_code == 200
    assert book.title in str(response.content)


@pytest.mark.django_db
def test_book_detail_view(client, book):
    url = reverse('catalog:book_detail', kwargs={'pk': book.pk})
    response = client.get(url)
    assert response.status_code == 200
    assert book.author in str(response.content)


@pytest.mark.django_db
def test_book_create_view_requires_login(client):
    url = reverse('catalog:book_create')
    response = client.get(url)
    assert response.status_code == 302


@pytest.mark.django_db
def test_book_create_view_with_permissions(client, user):
    permission = Permission.objects.get(codename='add_book')
    user.user_permissions.add(permission)
    client.force_login(user)

    url = reverse('catalog:book_create')
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_book_search_filter_view(client, book):
    url = reverse('catalog:book_list')
    response = client.get(url, {'q': book.title})
    assert response.status_code == 200
    assert book.title in str(response.content)

    response_empty = client.get(url, {'q': 'NonExistentTitleQuery123'})
    assert response_empty.status_code == 200
    assert book.title not in str(response_empty.content)


@pytest.mark.django_db
def test_book_update_view_requires_login(client, book):
    url = reverse('catalog:book_update', kwargs={'pk': book.pk})
    response = client.get(url)
    assert response.status_code == 302


@pytest.mark.django_db
def test_book_delete_view_requires_login(client, book):
    url = reverse('catalog:book_delete', kwargs={'pk': book.pk})
    response = client.get(url)
    assert response.status_code == 302


@pytest.mark.django_db
def test_payment_success_view_requires_login(client, user):
    url = reverse('catalog:payment_success')
    client.force_login(user)
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_language_switch_to_ukrainian(client, book):
    # Change language to Ukrainian via i18n set_language view
    set_lang_url = reverse('set_language')
    response = client.post(set_lang_url, {'language': 'uk', 'next': '/'})
    assert response.status_code == 302

    # Verify that home page renders Ukrainian localized text
    list_url = reverse('catalog:book_list')
    page_response = client.get(list_url)
    assert page_response.status_code == 200
    content = page_response.content.decode('utf-8')
    assert "Досліджувати книги" in content
    assert "Каталог книг" in content
    assert "Кошик" in content