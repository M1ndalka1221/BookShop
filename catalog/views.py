from decimal import Decimal

import stripe
from django.urls import reverse_lazy, reverse
from django.conf import settings
from django.db.models import Q
from django.db import transaction
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from .models import Book, Order, OrderItem
from .cart import Cart

# Create your views here.

stripe.api_key = settings.STRIPE_SECRET_KEY


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

class BookDetailView(DetailView):
    model = Book
    template_name = "catalog/book_detail.html"
    context_object_name = "book"


class CustomPermissionRequiredMixin(PermissionRequiredMixin):
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "⛔ You do not have permission to perform this action.")
            return redirect('catalog:book_list')

        return super().handle_no_permission()


class BookCreateView(LoginRequiredMixin, CustomPermissionRequiredMixin, CreateView):
    model = Book
    template_name = 'catalog/book_form.html'
    fields = ['category', 'title', 'author', 'price', 'description', 'stock']
    success_url = reverse_lazy('catalog:book_list')
    permission_required = 'catalog.add_book'

class BookUpdateView(LoginRequiredMixin, CustomPermissionRequiredMixin, UpdateView):
    model = Book
    template_name = 'catalog/book_form.html'
    fields = ['category', 'title', 'author', 'price', 'description', 'stock']
    permission_required = 'catalog.change_book'

    def get_success_url(self):
        return reverse_lazy('catalog:book_detail', kwargs={'pk': self.object.pk})


class BookDeleteView(LoginRequiredMixin, CustomPermissionRequiredMixin, DeleteView):
    model = Book
    template_name = 'catalog/book_confirm_delete.html'
    success_url = reverse_lazy('catalog:book_list')
    permission_required = 'catalog.delete_book'


@login_required
def cart_detail(request):
    cart = Cart(request)
    return render(request, 'catalog/cart_detail.html', {'cart': cart})


@login_required
def cart_add(request, book_id):
    cart = Cart(request)
    book = get_object_or_404(Book, id=book_id)
    if book.stock < 1:
        messages.error(request, f"Sorry, '{book.title}' is currently out of stock.")
        return redirect('catalog:book_list')
    cart.add(book=book)
    return redirect('catalog:cart_detail')


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


@login_required
def payment_success(request):
    return render(request, 'catalog/success.html')