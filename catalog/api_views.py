from decimal import Decimal
from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Category, Book, Order, OrderItem
from .cart import Cart
from .permissions import IsAdminUserOrReadOnly, IsOwner
from .serializers import (
    CategorySerializer,
    BookReadSerializer,
    BookWriteSerializer,
    OrderSerializer,
    CartSerializer
)

class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Category CRUD.
    Public read access; admin-only write operations.
    """
    queryset = Category.objects.annotate(books_count=Count('books')).order_by('id')
    serializer_class = CategorySerializer
    permission_classes = [IsAdminUserOrReadOnly]
    search_fields = ['name', 'slug']
    ordering_fields = ['id', 'name']


class BookViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Book CRUD with pagination, filtering, search, and ordering.
    Public read access; admin-only write operations.
    """
    queryset = Book.objects.select_related('category').all().order_by('id')
    permission_classes = [IsAdminUserOrReadOnly]
    filterset_fields = ['category', 'category__slug', 'stock']
    search_fields = ['title', 'author']
    ordering_fields = ['id', 'price', 'title']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return BookWriteSerializer
        return BookReadSerializer


class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user Orders.
    Authenticated users can view and create their own orders. Staff can view all orders.
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Order.objects.none()
        if user.is_staff:
            return Order.objects.prefetch_related('items__book__category').all()
        return Order.objects.prefetch_related('items__book__category').filter(user=user)

    def perform_create(self, serializer):
        order = serializer.save(user=self.request.user)
        # Check if user has items in session cart and populate order items automatically if present
        cart = Cart(self.request)
        if len(cart) > 0:
            order_items = []
            for item in cart:
                order_items.append(OrderItem(
                    order=order,
                    book=item['book'],
                    price=item['price'],
                    quantity=item['quantity']
                ))
            OrderItem.objects.bulk_create(order_items)
            cart.clear()


class CartViewSet(viewsets.ViewSet):
    """
    Custom ViewSet wrapping session-backed Cart operations.
    Endpoints:
    - GET /api/cart/ : list cart items and total
    - POST /api/cart/add/ : add item to cart
    - POST /api/cart/remove/ : remove item from cart
    - POST /api/cart/clear/ : clear cart
    """
    permission_classes = [permissions.AllowAny]

    def _serialize_cart(self, request) -> dict:
        cart = Cart(request)
        items = []
        for item in cart:
            items.append({
                'book_id': item['book'].id,
                'title': item['book'].title,
                'price': Decimal(str(item['price'])),
                'quantity': item['quantity'],
                'total_price': Decimal(str(item['total_price']))
            })
        data = {
            'items': items,
            'total_price': Decimal(str(cart.get_total_price())),
            'total_items': len(cart)
        }
        serializer = CartSerializer(data)
        return serializer.data

    def list(self, request):
        return Response(self._serialize_cart(request))

    @action(detail=False, methods=['post'], url_path='add')
    def add_item(self, request):
        book_id = request.data.get('book_id')
        if not book_id:
            return Response({'error': 'book_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        book = get_object_or_404(Book, id=book_id)
        try:
            quantity = int(request.data.get('quantity', 1))
        except (ValueError, TypeError):
            quantity = 1
        
        override_quantity = bool(request.data.get('override_quantity', False))
        
        cart = Cart(request)
        cart.add(book=book, quantity=quantity, override_quantity=override_quantity)
        return Response(self._serialize_cart(request), status=status.HTTP_200_OK)

    @action(detail=False, methods=['post', 'delete'], url_path='remove')
    def remove_item(self, request):
        book_id = request.data.get('book_id')
        if not book_id:
            return Response({'error': 'book_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        book = get_object_or_404(Book, id=book_id)
        cart = Cart(request)
        cart.remove(book=book)
        return Response(self._serialize_cart(request), status=status.HTTP_200_OK)

    @action(detail=False, methods=['post', 'delete'], url_path='clear')
    def clear_cart(self, request):
        cart = Cart(request)
        cart.clear()
        return Response(self._serialize_cart(request), status=status.HTTP_200_OK)
