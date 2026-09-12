import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from users.models import CustomUser


class Command(BaseCommand):
    help = "Sets up initial groups, permissions, and default service account for inter-service JWT auth."

    def handle(self, *args, **options):
        # Create standard groups
        manager_group, _ = Group.objects.get_or_create(name="Warehouse Managers")
        operator_group, _ = Group.objects.get_or_create(name="Warehouse Operators")
        service_group, _ = Group.objects.get_or_create(name="Service Clients")

        self.stdout.write(self.style.SUCCESS("Verified groups: Managers, Operators, Service Clients."))

        # Create or update service account for Project A
        svc_username = os.getenv("SERVICE_ACCOUNT_USERNAME", "bookshop_service")
        svc_password = os.getenv("SERVICE_ACCOUNT_PASSWORD", "warehouse_secret_pass_2026")

        service_user, created = CustomUser.objects.get_or_create(
            username=svc_username,
            defaults={
                "role": CustomUser.Role.SERVICE_ACCOUNT,
                "is_staff": True,
                "email": "service@bookshop.local",
            },
        )
        service_user.set_password(svc_password)
        service_user.role = CustomUser.Role.SERVICE_ACCOUNT
        service_user.save()
        service_user.groups.add(service_group)

        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(f"{action} service account '{svc_username}' for Project A communication.")
        )
