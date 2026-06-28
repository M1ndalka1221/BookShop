from django.shortcuts import render
from django.db.models import Count, Q
from .models import Book, Category
# Create your views here.

def catalog_dashboard(request):
    available_books = Book.objects.filter(stock__gt=0)
    search_results = Book.objects.filter(Q(title__icontains="Django") | Q(author__icontains="Python"))
    categories_with_count = Category.objects.annotate(books_count=Count('books'))
    context = {
        "available_books": available_books,
        "search_results": search_results,
        "categories": categories_with_count,
    }

    return render(request, 'catalog/dashboard.html', context)