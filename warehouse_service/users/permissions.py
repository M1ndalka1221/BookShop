from rest_framework import permissions


class IsWarehouseManager(permissions.BasePermission):
    """
    Permission check for Warehouse Managers and Admins.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_manager or request.user.is_superuser)
        )


class IsServiceAccountOrStaff(permissions.BasePermission):
    """
    Permission check for inter-service callers (e.g. Project A) or internal warehouse staff.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_service_account
                or request.user.is_operator
                or request.user.is_staff
                or request.user.is_superuser
            )
        )


class IsWarehouseStaff(permissions.BasePermission):
    """
    Permission check for operators and managers.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_operator or request.user.is_superuser)
        )
