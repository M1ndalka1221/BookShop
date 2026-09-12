from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", _("Admin")
        WAREHOUSE_MANAGER = "manager", _("Warehouse Manager")
        WAREHOUSE_OPERATOR = "operator", _("Warehouse Operator")
        SERVICE_ACCOUNT = "service", _("Service Account")

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.WAREHOUSE_OPERATOR,
        verbose_name=_("Role"),
    )
    phone_number = models.CharField(
        max_length=20, blank=True, verbose_name=_("Phone Number")
    )

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")

    @property
    def is_manager(self):
        return self.is_superuser or self.role == self.Role.WAREHOUSE_MANAGER

    @property
    def is_service_account(self):
        return self.role == self.Role.SERVICE_ACCOUNT

    @property
    def is_operator(self):
        return self.is_superuser or self.role in (
            self.Role.WAREHOUSE_OPERATOR,
            self.Role.WAREHOUSE_MANAGER,
        )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
