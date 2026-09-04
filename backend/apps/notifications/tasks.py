from celery import shared_task

from .services.notification_services import send_notification_message


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_notification_task(self, message_id: str):
    """
    Celery background task for delivering notification messages asynchronously.
    """
    success = send_notification_message(message_id)
    if not success:
        self.retry(exc=Exception(f"Failed to deliver notification {message_id}"))
    return success
