import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from catalog.models import Category, Book, Order, OrderItem

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        username="testuser",
        email="testuser@example.com",
        password="Password123!"
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="otheruser",
        email="otheruser@example.com",
        password="Password123!"
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="adminuser",
        email="adminuser@example.com",
        password="AdminPassword123!"
    )


@pytest.fixture
def sample_category(db):
    return Category.objects.create(name="Fiction", slug="fiction")


@pytest.fixture
def sample_book(db, sample_category):
    return Book.objects.create(
        category=sample_category,
        title="The Great Gatsby",
        author="F. Scott Fitzgerald",
        price=Decimal("12.99"),
        description="A classic novel.",
        stock=10
    )


# --- JWT Authentication Tests ---

@pytest.mark.django_db
def test_token_obtain_pair_success(api_client, regular_user):
    url = reverse("token_obtain_pair")
    response = api_client.post(url, {"username": "testuser", "password": "Password123!"}, format="json")
    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data
    assert "refresh" in response.data


@pytest.mark.django_db
def test_token_obtain_pair_invalid_credentials(api_client, regular_user):
    url = reverse("token_obtain_pair")
    response = api_client.post(url, {"username": "testuser", "password": "WrongPassword"}, format="json")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_token_refresh_success(api_client, regular_user):
    obtain_url = reverse("token_obtain_pair")
    token_resp = api_client.post(obtain_url, {"username": "testuser", "password": "Password123!"}, format="json")
    refresh_token = token_resp.data["refresh"]

    refresh_url = reverse("token_refresh")
    response = api_client.post(refresh_url, {"refresh": refresh_token}, format="json")
    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data


@pytest.mark.django_db
def test_token_verify_success(api_client, regular_user):
    obtain_url = reverse("token_obtain_pair")
    token_resp = api_client.post(obtain_url, {"username": "testuser", "password": "Password123!"}, format="json")
    access_token = token_resp.data["access"]

    verify_url = reverse("token_verify")
    response = api_client.post(verify_url, {"token": access_token}, format="json")
    assert response.status_code == status.HTTP_200_OK


# --- Category API Tests ---

@pytest.mark.django_db
def test_category_list_api(api_client, sample_category):
    url = reverse("category-list")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    results = response.data["results"] if "results" in response.data else response.data
    assert len(results) >= 1
    assert results[0]["name"] == "Fiction"


@pytest.mark.django_db
def test_category_detail_api(api_client, sample_category):
    url = reverse("category-detail", args=[sample_category.id])
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["slug"] == "fiction"


@pytest.mark.django_db
def test_category_create_by_admin(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    url = reverse("category-list")
    payload = {"name": "Science Fiction", "slug": "sci-fi"}
    response = api_client.post(url, payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert Category.objects.filter(slug="sci-fi").exists()


@pytest.mark.django_db
def test_category_create_by_regular_user_forbidden(api_client, regular_user):
    api_client.force_authenticate(user=regular_user)
    url = reverse("category-list")
    payload = {"name": "Science Fiction", "slug": "sci-fi"}
    response = api_client.post(url, payload, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_category_delete_by_admin(api_client, admin_user, sample_category):
    api_client.force_authenticate(user=admin_user)
    url = reverse("category-detail", args=[sample_category.id])
    response = api_client.delete(url)
    assert response.status_code == status.HTTP_24_NO_CONTENT if hasattr(status, "HTTP_24_NO_CONTENT") else response.status_code in [204, 200]
    assert not Category.objects.filter(id=sample_category.id).exists()


# --- Book API Tests ---

@pytest.mark.django_db
def test_book_list_pagination(api_client, sample_category):
    # Create 25 books to trigger 20 items per page pagination
    for i in range(25):
        Book.objects.create(
            category=sample_category,
            title=f"Book {i+1}",
            author="Author Name",
            price=Decimal("10.00"),
            description="Test book",
            stock=5
        )
    url = reverse("book-list")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 25
    assert len(response.data["results"]) == 20  # Page size is 20


@pytest.mark.django_db
def test_book_filter_by_category(api_client):
    cat1 = Category.objects.create(name="Cat 1", slug="cat-1")
    cat2 = Category.objects.create(name="Cat 2", slug="cat-2")
    Book.objects.create(category=cat1, title="Book 1", author="A", price=10, description="", stock=5)
    Book.objects.create(category=cat2, title="Book 2", author="B", price=15, description="", stock=5)

    url = f"{reverse('book-list')}?category__slug=cat-1"
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    results = response.data["results"]
    assert len(results) == 1
    assert results[0]["title"] == "Book 1"


@pytest.mark.django_db
def test_book_search_by_title_and_author(api_client, sample_category):
    Book.objects.create(category=sample_category, title="Django Deep Dive", author="Jane Doe", price=20, description="", stock=5)
    Book.objects.create(category=sample_category, title="Python Basics", author="John Smith", price=15, description="", stock=5)

    url = f"{reverse('book-list')}?search=Django"
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["title"] == "Django Deep Dive"


@pytest.mark.django_db
def test_book_ordering_by_price(api_client, sample_category):
    Book.objects.create(category=sample_category, title="Book Expensive", author="A", price=50, description="", stock=5)
    Book.objects.create(category=sample_category, title="Book Cheap", author="B", price=5, description="", stock=5)

    url = f"{reverse('book-list')}?ordering=price"
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    results = response.data["results"]
    assert float(results[0]["price"]) == 5.0
    assert float(results[1]["price"]) == 50.0


@pytest.mark.django_db
def test_book_create_by_admin(api_client, admin_user, sample_category):
    api_client.force_authenticate(user=admin_user)
    url = reverse("book-list")
    payload = {
        "category": sample_category.id,
        "title": "New Book",
        "author": "New Author",
        "price": "29.99",
        "description": "New description",
        "stock": 100
    }
    response = api_client.post(url, payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert Book.objects.filter(title="New Book").exists()


@pytest.mark.django_db
def test_book_create_by_regular_user_forbidden(api_client, regular_user, sample_category):
    api_client.force_authenticate(user=regular_user)
    url = reverse("book-list")
    payload = {
        "category": sample_category.id,
        "title": "Unauthorized Book",
        "author": "Author",
        "price": "10.00",
        "description": "Desc",
        "stock": 1
    }
    response = api_client.post(url, payload, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_book_detail_read_nested_category(api_client, sample_book):
    url = reverse("book-detail", args=[sample_book.id])
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["title"] == "The Great Gatsby"
    assert isinstance(response.data["category"], dict)
    assert response.data["category"]["name"] == "Fiction"


# --- Cart API Tests ---

@pytest.mark.django_db
def test_cart_get_empty(api_client):
    url = reverse("cart-list")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["items"] == []
    assert response.data["total_items"] == 0


@pytest.mark.django_db
def test_cart_add_item(api_client, sample_book):
    url = reverse("cart-add-item")
    payload = {"book_id": sample_book.id, "quantity": 2}
    response = api_client.post(url, payload, format="json")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["items"]) == 1
    assert response.data["items"][0]["quantity"] == 2
    assert response.data["total_items"] == 2


@pytest.mark.django_db
def test_cart_update_quantity(api_client, sample_book):
    add_url = reverse("cart-add-item")
    api_client.post(add_url, {"book_id": sample_book.id, "quantity": 2}, format="json")

    # Override quantity to 5
    response = api_client.post(add_url, {"book_id": sample_book.id, "quantity": 5, "override_quantity": True}, format="json")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["items"][0]["quantity"] == 5


@pytest.mark.django_db
def test_cart_remove_item(api_client, sample_book):
    add_url = reverse("cart-add-item")
    api_client.post(add_url, {"book_id": sample_book.id, "quantity": 2}, format="json")

    remove_url = reverse("cart-remove-item")
    response = api_client.post(remove_url, {"book_id": sample_book.id}, format="json")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["items"] == []
    assert response.data["total_items"] == 0


@pytest.mark.django_db
def test_cart_clear(api_client, sample_book):
    add_url = reverse("cart-add-item")
    api_client.post(add_url, {"book_id": sample_book.id, "quantity": 2}, format="json")

    clear_url = reverse("cart-clear-cart")
    response = api_client.post(clear_url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["items"] == []


# --- Order API Tests ---

@pytest.mark.django_db
def test_order_list_unauthenticated_forbidden(api_client):
    url = reverse("order-list")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_order_list_returns_user_orders_only(api_client, regular_user, other_user):
    Order.objects.create(user=regular_user)
    Order.objects.create(user=other_user)

    api_client.force_authenticate(user=regular_user)
    url = reverse("order-list")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    results = response.data["results"] if "results" in response.data else response.data
    assert len(results) == 1
    assert results[0]["user"] == regular_user.id


@pytest.mark.django_db
def test_order_detail_owner_access(api_client, regular_user):
    order = Order.objects.create(user=regular_user)
    api_client.force_authenticate(user=regular_user)
    url = reverse("order-detail", args=[order.id])
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == order.id


@pytest.mark.django_db
def test_order_detail_other_user_forbidden(api_client, regular_user, other_user):
    order = Order.objects.create(user=regular_user)
    api_client.force_authenticate(user=other_user)
    url = reverse("order-detail", args=[order.id])
    response = api_client.get(url)
    assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN]


@pytest.mark.django_db
def test_order_create_api(api_client, regular_user, sample_book):
    # First add book to session cart
    add_url = reverse("cart-add-item")
    api_client.post(add_url, {"book_id": sample_book.id, "quantity": 3}, format="json")

    # Now create order as authenticated user
    api_client.force_authenticate(user=regular_user)
    order_url = reverse("order-list")
    response = api_client.post(order_url, {}, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["user"] == regular_user.id
    assert len(response.data["items"]) == 1
    assert response.data["items"][0]["quantity"] == 3


@pytest.mark.django_db
def test_api_docs_swagger_accessible(api_client):
    url = reverse("swagger-ui")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
