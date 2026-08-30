import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.core.management import call_command
from catalog.models import Book, Order

logger = logging.getLogger(__name__)


@shared_task
def send_email_async(subject: str, message: str, recipient_list: list[str], from_email: str = None):
    """
    Asynchronously send an email notification.
    """
    if from_email is None:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@bookstore.com')
    try:
        sent_count = send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=False
        )
        logger.info(f"Async email sent to {recipient_list}, count: {sent_count}")
        return sent_count
    except Exception as e:
        logger.error(f"Failed to send async email to {recipient_list}: {e}")
        raise e


@shared_task
def generate_reports():
    """
    Asynchronously generate catalog and sales summary reports.
    """
    total_books = Book.objects.count()
    total_orders = Order.objects.count()
    paid_orders = Order.objects.filter(paid=True).count()
    
    report_data = {
        'total_books': total_books,
        'total_orders': total_orders,
        'paid_orders': paid_orders,
    }
    logger.info(f"Generated Catalog & Sales Report: {report_data}")
    return report_data


@shared_task
def cleanup_sessions():
    """
    Asynchronously clean up expired Django sessions.
    """
    try:
        call_command('clearsessions')
        logger.info("Successfully cleaned up expired sessions via Celery task.")
        return True
    except Exception as e:
        logger.error(f"Error during session cleanup task: {e}")
        raise e
