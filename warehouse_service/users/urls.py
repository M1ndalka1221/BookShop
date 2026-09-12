from django.urls import path
from .views import CurrentUserProfileView, UserListCreateView

app_name = "users"

urlpatterns = [
    path("me/", CurrentUserProfileView.as_view(), name="user_profile"),
    path("", UserListCreateView.as_view(), name="user_list_create"),
]
