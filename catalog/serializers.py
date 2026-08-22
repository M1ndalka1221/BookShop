from decimal import Decimal
from rest_framework import serializers
from .models import Category, Book, Order, OrderItem

class CategorySerializer(serializers.ModelSerializer):
    books_count = serializers.IntegerField(read_only=True, required=False, default=0)

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'books_count']


class BookReadSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Book
        fields = ['id', 'category', 'title', 'author', 'price', 'description', 'stock']


class BookWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['id', 'category', 'title', 'author', 'price', 'description', 'stock']


class OrderItemSerializer(serializers.ModelSerializer):
    book = BookReadSerializer(read_only=True)
    cost = serializers.DecimalField(source='get_cost', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'book', 'price', 'quantity', 'cost']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total_cost = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'user', 'created_at', 'paid', 'stripe_id', 'items', 'total_cost']
        read_only_fields = ['user', 'created_at', 'stripe_id']

    def get_total_cost(self, obj: Order) -> Decimal:
        return sum(item.get_cost() for item in obj.items.all())


class CartItemSerializer(serializers.Serializer):
    book_id = serializers.IntegerField()
    title = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    quantity = serializers.IntegerField()
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2)


class CartSerializer(serializers.Serializer):
    items = CartItemSerializer(many=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_items = serializers.IntegerField()
