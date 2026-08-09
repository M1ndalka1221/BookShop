from django.http import JsonResponse
from .models import Book, Category, Order
from asgiref.sync import sync_to_async

async def async_book_count(request):
    count = await Book.objects.acount()
    return JsonResponse({'total_books': count})

async def async_categories_list(request):
    categories = await sync_to_async(list)(Category.objects.values('name', 'slug'))
    return JsonResponse({'categories': categories})

async def async_order_status(request, order_id):
    try:
        order = await Order.objects.aget(id=order_id)
        status = 'Paid' if order.paid else 'Pending'
    except Order.DoesNotExist:
        status = 'Not Found'
    return JsonResponse({'order_id': order_id, 'status': status})