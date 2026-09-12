import pytest
from django.core.management import call_command
from rest_framework.test import APIClient
from rest_framework import status
from users.models import CustomUser
from users.permissions import (
    IsWarehouseManager,
    IsServiceAccountOrStaff,
    IsWarehouseStaff,
)


class DummyRequest:
    def __init__(self, user):
        self.user = user


@pytest.mark.django_db
def test_custom_user_roles_and_properties():
    manager = CustomUser.objects.create_user(
        username="manager1",
        password="password123",
        role=CustomUser.Role.WAREHOUSE_MANAGER,
    )
    assert manager.is_manager is True
    assert manager.is_service_account is False
    assert manager.is_operator is True
    assert "manager1" in str(manager)

    service_user = CustomUser.objects.create_user(
        username="svc1",
        password="password123",
        role=CustomUser.Role.SERVICE_ACCOUNT,
    )
    assert service_user.is_manager is False
    assert service_user.is_service_account is True
    assert service_user.is_operator is False

    operator = CustomUser.objects.create_user(
        username="op1",
        password="password123",
        role=CustomUser.Role.WAREHOUSE_OPERATOR,
    )
    assert operator.is_manager is False
    assert operator.is_service_account is False
    assert operator.is_operator is True


@pytest.mark.django_db
def test_permission_classes():
    manager = CustomUser.objects.create_user(
        username="manager2",
        password="password123",
        role=CustomUser.Role.WAREHOUSE_MANAGER,
    )
    operator = CustomUser.objects.create_user(
        username="op2", password="password123", role=CustomUser.Role.WAREHOUSE_OPERATOR
    )
    service_user = CustomUser.objects.create_user(
        username="svc2", password="password123", role=CustomUser.Role.SERVICE_ACCOUNT
    )

    perm_mgr = IsWarehouseManager()
    perm_service = IsServiceAccountOrStaff()
    perm_staff = IsWarehouseStaff()

    # Manager permissions
    assert perm_mgr.has_permission(DummyRequest(manager), None) is True
    assert perm_service.has_permission(DummyRequest(manager), None) is True
    assert perm_staff.has_permission(DummyRequest(manager), None) is True

    # Operator permissions
    assert perm_mgr.has_permission(DummyRequest(operator), None) is False
    assert perm_service.has_permission(DummyRequest(operator), None) is True
    assert perm_staff.has_permission(DummyRequest(operator), None) is True

    # Service user permissions
    assert perm_mgr.has_permission(DummyRequest(service_user), None) is False
    assert perm_service.has_permission(DummyRequest(service_user), None) is True
    assert perm_staff.has_permission(DummyRequest(service_user), None) is False


@pytest.mark.django_db
def test_setup_roles_command():
    call_command("setup_roles")
    svc_user = CustomUser.objects.get(username="bookshop_service")
    assert svc_user.role == CustomUser.Role.SERVICE_ACCOUNT
    assert svc_user.groups.filter(name="Service Clients").exists()


@pytest.mark.django_db
def test_user_api_views():
    client = APIClient()
    manager = CustomUser.objects.create_user(
        username="admin_mgr",
        password="password123",
        role=CustomUser.Role.WAREHOUSE_MANAGER,
    )
    operator = CustomUser.objects.create_user(
        username="worker",
        password="password123",
        role=CustomUser.Role.WAREHOUSE_OPERATOR,
    )

    # Anonymous access rejected
    res = client.get("/api/users/me/")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED

    # Operator profile access
    client.force_authenticate(user=operator)
    res = client.get("/api/users/me/")
    assert res.status_code == status.HTTP_200_OK
    assert res.data["username"] == "worker"

    # Operator cannot list all users
    res = client.get("/api/users/")
    assert res.status_code == status.HTTP_403_FORBIDDEN

    # Manager can list users
    client.force_authenticate(user=manager)
    res = client.get("/api/users/")
    assert res.status_code == status.HTTP_200_OK
    assert res.data["count"] >= 2
