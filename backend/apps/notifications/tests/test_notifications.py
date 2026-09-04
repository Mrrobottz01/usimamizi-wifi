import pytest
from django.contrib.auth import get_user_model

from apps.companies.services.company_services import create_company
from apps.notifications.models import NotificationStatus
from apps.notifications.services.notification_services import queue_notification, send_notification

User = get_user_model()


@pytest.mark.django_db
def test_notification_queue_and_delivery():
    user = User.objects.create_user(email='notif_test@example.com', password='Password123!')
    company = create_company(name='Notif Co', user=user)

    msg = queue_notification(
        company=company,
        recipient='+255712345678',
        channel='SMS',
        rendered_content='Test content'
    )

    assert msg.status == NotificationStatus.QUEUED

    processed = send_notification(notification_id=str(msg.id))
    assert processed is not None
    assert processed.status == NotificationStatus.SENT
