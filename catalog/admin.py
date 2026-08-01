from django.contrib import admin
from .models import Category, Book, Order, OrderItem
# Register your models here.
class BookInline(admin.TabularInline):
    model = Book
    extra = 1

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['book']
    extra = 0

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', "slug")
    prepopulated_fields = {'slug': ('name',)}
    inlines = [BookInline]

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "price", "stock")
    list_filter = ("category", "author")
    search_fields = ("title", "author", "description")
    list_editable = ("price", "stock")

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'paid', 'created_at']
    list_filter = ['paid', 'created_at']
    inlines = [OrderItemInline]