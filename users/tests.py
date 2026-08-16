# Generated with AI, reviewed and modified
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_custom_user_creation():
    """Test creation of CustomUser instance and string representation."""
    user = User.objects.create_user(username="testuser", email="test@example.com", password="password123", bio="Book lover")
    assert user.username == "testuser"
    assert str(user) == "testuser"
    assert user.bio == "Book lover"


@pytest.mark.django_db
def test_custom_user_default_bio():
    """Test CustomUser default bio is None when not specified."""
    user = User.objects.create_user(username="reader", email="reader@example.com", password="password123")
    assert user.bio is None
