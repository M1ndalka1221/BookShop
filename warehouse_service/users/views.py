from rest_framework import generics, permissions
from .models import CustomUser
from .serializers import UserSerializer, UserProfileSerializer
from .permissions import IsWarehouseManager


class CurrentUserProfileView(generics.RetrieveUpdateAPIView):
    """
    CBV to retrieve and update the authenticated user's profile.
    """

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserListCreateView(generics.ListCreateAPIView):
    """
    CBV for Warehouse Managers to list and create users.
    """

    queryset = CustomUser.objects.all().order_by("id")
    serializer_class = UserSerializer
    permission_classes = [IsWarehouseManager]
