from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Name")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="URL Slug")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"


class Book(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="books", verbose_name="Category")
    title = models.CharField(max_length=100, verbose_name="Title")
    author = models.CharField(max_length=100, verbose_name="Author")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Price")
    description = models.TextField(verbose_name="Description")
    stock = models.PositiveIntegerField(default=0, verbose_name="Stock")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Book"
        verbose_name_plural = "Books"
