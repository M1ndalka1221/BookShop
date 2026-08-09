import pytest
from users.forms import CustomUserCreationForm
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_custom_user_creation_form_valid():
    form_data = {
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password1': 'StrongPass123!',
        'password2': 'StrongPass123!',
    }
    form = CustomUserCreationForm(data=form_data)
    assert form.is_valid(), form.errors
    user = form.save()
    assert user.username == 'newuser'
    assert user.email == 'newuser@example.com'


@pytest.mark.django_db
def test_custom_user_creation_form_passwords_mismatch():
    form_data = {
        'username': 'newuser2',
        'email': 'newuser2@example.com',
        'password1': 'StrongPass123!',
        'password2': 'DifferentPass123!',
    }
    form = CustomUserCreationForm(data=form_data)
    assert not form.is_valid()
    assert 'password2' in form.errors


@pytest.mark.django_db
def test_custom_user_creation_form_missing_username():
    form_data = {
        'username': '',
        'email': 'nousername@example.com',
        'password1': 'StrongPass123!',
        'password2': 'StrongPass123!',
    }
    form = CustomUserCreationForm(data=form_data)
    assert not form.is_valid()
    assert 'username' in form.errors


@pytest.mark.django_db
def test_custom_user_creation_form_duplicate_username(user):
    form_data = {
        'username': user.username,
        'email': 'duplicate@example.com',
        'password1': 'StrongPass123!',
        'password2': 'StrongPass123!',
    }
    form = CustomUserCreationForm(data=form_data)
    assert not form.is_valid()
    assert 'username' in form.errors
