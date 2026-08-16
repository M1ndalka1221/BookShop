# AI Code Review Report - BookShop Project

This document contains the AI Code Review conducted for 3 key views in the **BookShop** Django application, including the original source code, AI feedback/recommendations, and the final refactored code.

---

## View 1: `checkout` (`catalog/views.py`)

### Original Code
```python
@login_required
def checkout(request):
    cart = Cart(request)
    if len(cart) == 0:
        messages.warning(request, "Your cart is empty.")
        return redirect('catalog:cart_detail')

    if request.method == 'POST':
        try:
            with transaction.atomic():
                book_ids = [item['book'].id for item in cart]
                books_db = {b.id: b for b in Book.objects.select_for_update().filter(id__in=book_ids)}

                # Check stock availability for all items before placing order
                for item in cart:
                    book = books_db.get(item['book'].id)
                    if not book or book.stock < item['quantity']:
                        messages.error(
                            request,
                            f"Sorry, '{item['book'].title}' does not have enough stock available."
                        )
                        return redirect('catalog:cart_detail')

                order = Order.objects.create(user=request.user)

                for item in cart:
                    OrderItem.objects.create(
                        order=order,
                        book=item['book'],
                        price=item['price'],
                        quantity=item['quantity']
                    )
                    book = books_db[item['book'].id]
                    book.stock -= item['quantity']
                    book.save()

                cart.clear()
                subject = f'Order nr. {order.id}'
                message = f'Dear {order.user.username},\n\nYou have successfully placed an order. Your order ID is {order.id}.'
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [order.user.email])

            session_data = {
                'mode': 'payment',
                'client_reference_id': order.id,
                'success_url': request.build_absolute_uri(reverse('catalog:payment_success')),
                'cancel_url': request.build_absolute_uri(reverse('catalog:cart_detail')),
                'line_items': []
            }

            for item in order.items.select_related('book').all():
                session_data['line_items'].append({
                    'price_data': {
                        'unit_amount': int(item.price * Decimal('100')),
                        'currency': 'usd',
                        'product_data': {
                            'name': item.book.title,
                        },
                    },
                    'quantity': item.quantity,
                })

            checkout_session = stripe.checkout.Session.create(**session_data)

            order.stripe_id = checkout_session.id
            order.save()
            response = HttpResponseRedirect(checkout_session.url)
            response.status_code = 303
            return response
        except stripe.error.StripeError as e:
            messages.error(request, f"Payment error: {str(e)}")
            return redirect('catalog:cart_detail')

    return render(request, 'catalog/checkout.html', {'cart': cart})
```

### AI Recommendations & Analysis
1. **Transaction Boundary Violation (Side-effects inside DB lock)**: `send_mail()` is invoked directly inside `with transaction.atomic():`. Network operations (SMTP/email) inside atomic blocks hold database row locks (`select_for_update`) open while waiting for external networks. If email sending fails or times out, it aborts the database transaction. **Recommendation**: Move `send_mail()` outside the atomic block and wrap it in a silent fallback.
2. **Database Query Optimization (Bulk Creation & Updates)**: `OrderItem.objects.create()` and `book.save()` execute inside a Python loop, triggering $N$ INSERT statements and $N$ UPDATE queries. **Recommendation**: Use `OrderItem.objects.bulk_create()` and `Book.objects.bulk_update()`.
3. **Type Annotations & Documentation**: The view lacks PEP 484 type hints and a docstring. **Recommendation**: Add explicit return types (`HttpResponse`) and Google-style docstrings.

### Final Refactored Code
```python
@login_required
def checkout(request: HttpRequest) -> HttpResponse:
    """
    Handle user checkout process including stock validation, transaction-safe order creation,
    cart clearing, notification mailing, and Stripe payment session initialization.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: Rendered checkout template for GET, or Stripe redirect/error redirect for POST.
    """
    cart = Cart(request)
    if len(cart) == 0:
        messages.warning(request, "Your cart is empty.")
        return redirect('catalog:cart_detail')

    if request.method == 'POST':
        try:
            with transaction.atomic():
                book_ids = [item['book'].id for item in cart]
                books_db = {b.id: b for b in Book.objects.select_for_update().filter(id__in=book_ids)}

                # Validate stock availability for all items before creating order
                for item in cart:
                    book = books_db.get(item['book'].id)
                    if not book or book.stock < item['quantity']:
                        messages.error(
                            request,
                            f"Sorry, '{item['book'].title}' does not have enough stock available."
                        )
                        return redirect('catalog:cart_detail')

                order = Order.objects.create(user=request.user)

                # Batch create OrderItems and update stock
                order_items = []
                books_to_update = []
                for item in cart:
                    order_items.append(OrderItem(
                        order=order,
                        book=item['book'],
                        price=item['price'],
                        quantity=item['quantity']
                    ))
                    book = books_db[item['book'].id]
                    book.stock -= item['quantity']
                    books_to_update.append(book)

                OrderItem.objects.bulk_create(order_items)
                Book.objects.bulk_update(books_to_update, ['stock'])
                cart.clear()

            # Email notification sent outside of DB transaction block
            try:
                subject = f'Order nr. {order.id}'
                message = f'Dear {order.user.username},\n\nYou have successfully placed an order. Your order ID is {order.id}.'
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [order.user.email])
            except Exception:
                # Log or handle email delivery issues without rolling back successful order
                pass

            session_data: dict[str, Any] = {
                'mode': 'payment',
                'client_reference_id': order.id,
                'success_url': request.build_absolute_uri(reverse('catalog:payment_success')),
                'cancel_url': request.build_absolute_uri(reverse('catalog:cart_detail')),
                'line_items': []
            }

            for item in order.items.select_related('book').all():
                session_data['line_items'].append({
                    'price_data': {
                        'unit_amount': int(item.price * Decimal('100')),
                        'currency': 'usd',
                        'product_data': {
                            'name': item.book.title,
                        },
                    },
                    'quantity': item.quantity,
                })

            checkout_session = stripe.checkout.Session.create(**session_data)

            order.stripe_id = checkout_session.id
            order.save()
            response = HttpResponseRedirect(checkout_session.url)
            response.status_code = 303
            return response
        except stripe.error.StripeError as e:
            messages.error(request, f"Payment error: {str(e)}")
            return redirect('catalog:cart_detail')

    return render(request, 'catalog/checkout.html', {'cart': cart})
```

---

## View 2: `BookListView` (`catalog/views.py`)

### Original Code
```python
class BookListView(ListView):
    model = Book
    template_name = "catalog/book_list.html"
    context_object_name = "books"
    paginate_by = 5

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get("q")
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(author__icontains=query)
            )
        return queryset
```

### AI Recommendations & Analysis
1. **N+1 Query Issue**: When accessing `book.category` in the list template, Django executes an additional query per book. **Recommendation**: Chain `.select_related("category")` onto `super().get_queryset()`.
2. **Whitespace Query Sanitization**: Searching for pure whitespace (e.g. `?q=   `) produces redundant filtering. **Recommendation**: Use `query.strip()` to strip leading/trailing whitespace.
3. **Type Annotations & Documentation**: Add `QuerySet[Book]` return type annotation and clear docstring documenting queryset customization.

### Final Refactored Code
```python
class BookListView(ListView):
    """
    Display a paginated list of books with optional search filtering.

    Filters books by matching the title or author against the 'q' query parameter.
    Uses select_related to optimize category prefetching and avoid N+1 queries.
    """
    model = Book
    template_name = "catalog/book_list.html"
    context_object_name = "books"
    paginate_by = 5

    def get_queryset(self) -> QuerySet[Book]:
        """
        Fetch the book queryset with select_related for categories and optional search query filter.

        Returns:
            QuerySet[Book]: Filtered or unfiltered book queryset.
        """
        queryset = super().get_queryset().select_related("category")
        query = self.request.GET.get("q")
        if query and query.strip():
            query_str = query.strip()
            queryset = queryset.filter(
                Q(title__icontains=query_str) | Q(author__icontains=query_str)
            )
        return queryset
```

---

## View 3: `async_order_status` (`catalog/async_views.py`)

### Original Code
```python
async def async_order_status(request, order_id):
    try:
        order = await Order.objects.aget(id=order_id)
        status = 'Paid' if order.paid else 'Pending'
    except Order.DoesNotExist:
        status = 'Not Found'
    return JsonResponse({'order_id': order_id, 'status': status})
```

### AI Recommendations & Analysis
1. **HTTP Status Code Compliance**: Returning `{ 'status': 'Not Found' }` with standard HTTP status 200 OK breaks API standards. **Recommendation**: Explicitly return `status=404` on `Order.DoesNotExist`.
2. **Type Annotations & Documentation**: Lacks parameter type hints (`HttpRequest`, `int`) and docstring detailing async behavior and error codes.

### Final Refactored Code
```python
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
```
