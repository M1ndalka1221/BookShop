from django.urls import reverse_lazy
from django.db.models import Q
from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from .models import Book

# Create your views here.

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
