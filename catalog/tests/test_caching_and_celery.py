import pytest
from unittest.mock import patch
from django.core.cache import cache
from django.urls import reverse
from catalog.models import Book, Category
from catalog.views import get_book_detail_cached
from catalog.tasks import send_email_async, generate_reports, cleanup_sessions


@pytest.mark.django_db
class TestRedisCachingAndSignals:

    @pytest.fixture(autouse=True)
    def clear_cache_fixture(self):
        cache.clear()
        yield
        cache.clear()

    def test_get_book_detail_cached(self, category):
        book = Book.objects.create(
            category=category,
            title="Caching Test Book",
            author="Cache Author",
            price=19.99,
            description="Caching description",
            stock=10
        )
        cache_key = f"book_detail_{book.id}"
        assert cache.get(cache_key) is None

        cached_book = get_book_detail_cached(book.id)
        assert cached_book.id == book.id
        assert cache.get(cache_key) is not None

    def test_post_save_signal_invalidates_cache(self, category):
        book = Book.objects.create(
            category=category,
            title="Signal Book",
            author="Author",
            price=29.99,
            description="Desc",
            stock=5
        )
        cache_key = f"book_detail_{book.id}"
        # Populate cache
        get_book_detail_cached(book.id)
        assert cache.get(cache_key) is not None

        # Modify book to fire post_save signal
        book.title = "Updated Signal Book Title"
        book.save()

        # Cache key should be invalidated by signal
        assert cache.get(cache_key) is None

    def test_post_delete_signal_invalidates_cache(self, category):
        book = Book.objects.create(
            category=category,
            title="Delete Signal Book",
            author="Author",
            price=15.00,
            description="Desc",
            stock=2
        )
        cache_key = f"book_detail_{book.id}"
        get_book_detail_cached(book.id)
        assert cache.get(cache_key) is not None

        book.delete()
        assert cache.get(cache_key) is None


@pytest.mark.django_db
class TestCeleryTasks:

    @patch("catalog.tasks.send_mail")
    def test_send_email_async(self, mock_send_mail):
        mock_send_mail.return_value = 1
        result = send_email_async("Test Subject", "Test Body", ["test@example.com"])
        assert result == 1
        mock_send_mail.assert_called_once_with(
            subject="Test Subject",
            message="Test Body",
            from_email="noreply@bookstore.com",
            recipient_list=["test@example.com"],
            fail_silently=False
        )

    def test_generate_reports(self, book):
        report = generate_reports()
        assert "total_books" in report
        assert "total_orders" in report
        assert "paid_orders" in report
        assert report["total_books"] >= 1

    @patch("catalog.tasks.call_command")
    def test_cleanup_sessions(self, mock_call_command):
        result = cleanup_sessions()
        assert result is True
        mock_call_command.assert_called_once_with("clearsessions")
