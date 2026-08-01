from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    path('', views.BookListView.as_view(), name='book_list'),
    path('book/<int:pk>/', views.BookDetailView.as_view(), name='book_detail'),
    path('book/add/', views.BookCreateView.as_view(), name='book_create'),
    path('book/<int:pk>/edit/', views.BookUpdateView.as_view(), name='book_update'),
    path('book/<int:pk>/delete/', views.BookDeleteView.as_view(), name='book_delete'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:book_id>/', views.cart_add, name='cart_add'),
    path('checkout/', views.checkout, name='checkout'),
    path('success/', views.payment_success, name='payment_success'),
]