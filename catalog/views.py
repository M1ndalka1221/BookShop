from decimal import Decimal
from typing import Any

import stripe
from django.urls import reverse_lazy, reverse
from django.conf import settings
from django.db.models import Q, QuerySet
from django.db import transaction
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from .models import Book, Order, OrderItem
from .cart import Cart
from .tasks import send_email_async

stripe.api_key = settings.STRIPE_SECRET_KEY


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


def get_book_detail_cached(book_id: int) -> Book:
    """
    Low-level cache retrieval for a Book object by primary key.
    """
    cache_key = f"book_detail_{book_id}"
    book = cache.get(cache_key)
    if book is None:
        book = get_object_or_404(Book.objects.select_related("category"), id=book_id)
        cache.set(cache_key, book, 600)
    return book


@method_decorator(cache_page(60 * 15), name='dispatch')
class BookDetailView(DetailView):
    """
    Display details of a single book instance with view-level and low-level caching.
    """
    model = Book
    template_name = "catalog/book_detail.html"
    context_object_name = "book"

    def get_object(self, queryset=None) -> Book:
        pk = self.kwargs.get(self.pk_url_kwarg)
        if pk is not None:
            return get_book_detail_cached(int(pk))
        return super().get_object(queryset)


class CustomPermissionRequiredMixin(PermissionRequiredMixin):
    """
    Custom permission mixin that redirects authenticated users with a friendly error message
    if they lack necessary permissions, instead of displaying a 403 response.
    """
    def handle_no_permission(self) -> HttpResponse:
        """
        Handle permission denial by adding an error message and redirecting if authenticated.

        Returns:
            HttpResponse: Redirect to book list or standard handle_no_permission response.
        """
        if self.request.user.is_authenticated:
            messages.error(self.request, "⛔ You do not have permission to perform this action.")
            return redirect('catalog:book_list')

        return super().handle_no_permission()


class BookCreateView(LoginRequiredMixin, CustomPermissionRequiredMixin, CreateView):
    """
    View for staff users to create a new book item.
    """
    model = Book
    template_name = 'catalog/book_form.html'
    fields = ['category', 'title', 'author', 'price', 'description', 'stock']
    success_url = reverse_lazy('catalog:book_list')
    permission_required = 'catalog.add_book'


class BookUpdateView(LoginRequiredMixin, CustomPermissionRequiredMixin, UpdateView):
    """
    View for staff users to update an existing book item.
    """
    model = Book
    template_name = 'catalog/book_form.html'
    fields = ['category', 'title', 'author', 'price', 'description', 'stock']
    permission_required = 'catalog.change_book'

    def get_success_url(self) -> str:
        """
        Return the success URL pointing to the book detail page.

        Returns:
            str: URL for the book detail view.
        """
        return reverse_lazy('catalog:book_detail', kwargs={'pk': self.object.pk})


class BookDeleteView(LoginRequiredMixin, CustomPermissionRequiredMixin, DeleteView):
    """
    View for staff users to confirm and delete a book item.
    """
    model = Book
    template_name = 'catalog/book_confirm_delete.html'
    success_url = reverse_lazy('catalog:book_list')
    permission_required = 'catalog.delete_book'


@login_required
def cart_detail(request: HttpRequest) -> HttpResponse:
    """
    Render the shopping cart details page.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: Rendered cart detail template.
    """
    cart = Cart(request)
    return render(request, 'catalog/cart_detail.html', {'cart': cart})


@login_required
def cart_add(request: HttpRequest, book_id: int) -> HttpResponse:
    """
    Add a specified book to the user's shopping cart if stock is available.

    Args:
        request (HttpRequest): The HTTP request object.
        book_id (int): Primary key of the book to add.

    Returns:
        HttpResponse: Redirect to book list if out of stock, or cart detail on success.
    """
    cart = Cart(request)
    book = get_object_or_404(Book, id=book_id)
    if book.stock < 1:
        messages.error(request, f"Sorry, '{book.title}' is currently out of stock.")
        return redirect('catalog:book_list')
    cart.add(book=book)
    return redirect('catalog:cart_detail')


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

            # Async email notification via Celery task
            try:
                subject = f'Order nr. {order.id}'
                message = f'Dear {order.user.username},\n\nYou have successfully placed an order. Your order ID is {order.id}.'
                send_email_async.delay(subject, message, [order.user.email])
            except Exception:
                # Fallback to sync send_mail if Celery broker is unavailable
                try:
                    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [order.user.email])
                except Exception:
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


@login_required
def payment_success(request: HttpRequest) -> HttpResponse:
    """
    Render payment success confirmation page.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: Rendered success page template.
    """
    return render(request, 'catalog/success.html')