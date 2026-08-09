from django.urls import path
from . import views, async_views

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
    path('api/async/books/count/', async_views.async_book_count, name='async_book_count'),
    path('api/async/categories/', async_views.async_categories_list, name='async_categories_list'),
    path('api/async/order/<int:order_id>/status/', async_views.async_order_status, name='async_order_status'),
]