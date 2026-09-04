from django.urls import path

from .views import (
    NotificationSettingsView,
    ProviderSenderIDsView,
    SendTestSMSView,
    SetDefaultSenderIDView,
    SMSHistoryDetailView,
    SMSHistoryExportView,
    SMSHistoryListView,
    SMSRetryView,
    SMSWebhookView,
    SyncProviderSenderIDsView,
)

urlpatterns = [
    # Settings & Provider Configuration
    path('settings/notifications/', NotificationSettingsView.as_view(), name='notification-settings'),
    path('settings/notifications/sms/providers/', NotificationSettingsView.as_view(), name='sms-providers-list'),
    path('settings/notifications/sms/providers/<uuid:id>/sender-ids/', ProviderSenderIDsView.as_view(), name='provider-sender-ids'),
    path('settings/notifications/sms/providers/<uuid:id>/sync-sender-ids/', SyncProviderSenderIDsView.as_view(), name='sync-provider-sender-ids'),
    path('settings/notifications/sms/providers/<uuid:id>/default-sender/', SetDefaultSenderIDView.as_view(), name='set-default-sender-id'),
    path('settings/notifications/test-sms/', SendTestSMSView.as_view(), name='send-test-sms'),

    # SMS History, Delivery Logs & Operational Actions
    path('notifications/sms/history/', SMSHistoryListView.as_view(), name='sms-history-list'),
    path('notifications/sms/history/export/', SMSHistoryExportView.as_view(), name='sms-history-export'),
    path('notifications/sms/history/<uuid:id>/', SMSHistoryDetailView.as_view(), name='sms-history-detail'),
    path('notifications/sms/history/<uuid:id>/retry/', SMSRetryView.as_view(), name='sms-history-retry'),

    # Delivery Webhook Handlers
    path('webhooks/sms/<str:provider>/', SMSWebhookView.as_view(), name='sms-webhook'),
]
