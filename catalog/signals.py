import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Book

logger = logging.getLogger(__name__)


def invalidate_book_cache(book_id: int):
    """
    Invalidate low-level, view, and template fragment cache keys for a given book ID.
    """
    keys_to_delete = [
        f"book_detail_{book_id}",
        "all_books_cache",
        "book_list_cache",
    ]
    for key in keys_to_delete:
        cache.delete(key)
    cache.clear()
    logger.info(f"Invalidated cache keys for book ID: {book_id}")


@receiver(post_save, sender=Book)
def book_post_save_handler(sender, instance: Book, created: bool, **kwargs):
    """
    Signal handler triggered after a Book instance is created or updated.
    """
    invalidate_book_cache(instance.id)


@receiver(post_delete, sender=Book)
def book_post_delete_handler(sender, instance: Book, **kwargs):
    """
    Signal handler triggered after a Book instance is deleted.
    """
    invalidate_book_cache(instance.id)
