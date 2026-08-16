from django.http import HttpRequest, JsonResponse
from .models import Book, Category, Order
from asgiref.sync import sync_to_async

async def async_book_count(request: HttpRequest) -> JsonResponse:
    """
    Asynchronously retrieve and return the total count of books in the database.

    Args:
        request (HttpRequest): The incoming HTTP request.

    Returns:
        JsonResponse: JSON response containing total book count.
    """
    count = await Book.objects.acount()
    return JsonResponse({'total_books': count})


async def async_categories_list(request: HttpRequest) -> JsonResponse:
    """
    Asynchronously fetch and return a list of all categories with their name and slug.

    Args:
        request (HttpRequest): The incoming HTTP request.

    Returns:
        JsonResponse: JSON response with category list.
    """
    categories = await sync_to_async(list)(Category.objects.values('name', 'slug'))
    return JsonResponse({'categories': categories})


async def async_order_status(request: HttpRequest, order_id: int) -> JsonResponse:
    """
    Asynchronously retrieve the status of an order by ID.

    Returns HTTP 200 with payment status if found, or HTTP 404 if the order does not exist.

    Args:
        request (HttpRequest): The incoming HTTP request.
        order_id (int): Primary key of the target order.

    Returns:
        JsonResponse: JSON object with order details and appropriate status code.
    """
    try:
        order = await Order.objects.aget(id=order_id)
        status = 'Paid' if order.paid else 'Pending'
        return JsonResponse({'order_id': order_id, 'status': status})
    except Order.DoesNotExist:
        return JsonResponse({'order_id': order_id, 'status': 'Not Found', 'error': 'Order does not exist'}, status=404)