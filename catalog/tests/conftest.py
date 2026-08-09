import pytest
import factory
from django.contrib.auth import get_user_model
from catalog.models import Category, Book, Order, OrderItem

User = get_user_model()

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.Sequence(lambda n: f'user{n}@example.com')
    password = 'password123'

class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category
    name = factory.Sequence(lambda n: f'Category {n}')
    slug = factory.Sequence(lambda n: f'category-{n}')

class BookFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Book
    category = factory.SubFactory(CategoryFactory)
    title = factory.Faker('sentence', nb_words=3)
    author = factory.Faker('name')
    price = 19.99
    stock = 10

class OrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Order
    user = factory.SubFactory(UserFactory)
    paid = False

class OrderItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrderItem
    order = factory.SubFactory(OrderFactory)
    book = factory.SubFactory(BookFactory)
    price = "19.99"
    quantity = 2

@pytest.fixture
def user():
    return UserFactory()

@pytest.fixture
def book():
    return BookFactory()

@pytest.fixture
def order():
    return OrderFactory()

@pytest.fixture
def category():
    return CategoryFactory()