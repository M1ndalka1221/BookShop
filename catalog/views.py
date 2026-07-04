from django.urls import reverse_lazy
from django.db.models import Q
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
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


class BookCreateView(CreateView):
    model = Book
    template_name = 'catalog/book_form.html'
    fields = ['category', 'title', 'author', 'price', 'description', 'stock']
    success_url = reverse_lazy('catalog:book_list')


class BookUpdateView(UpdateView):
    model = Book
    template_name = 'catalog/book_form.html'
    fields = ['category', 'title', 'author', 'price', 'description', 'stock']

    def get_success_url(self):
        return reverse_lazy('catalog:book_detail', kwargs={'pk': self.object.pk})


class BookDeleteView(DeleteView):
    model = Book
    template_name = 'catalog/book_confirm_delete.html'
    success_url = reverse_lazy('catalog:book_list')
