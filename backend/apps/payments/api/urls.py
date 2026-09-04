from django.urls import path

from apps.payments.api.views import (
    AccessPurchaseDetailView,
    AccessPurchaseListView,
    ApplyWalledGardenPresetView,
    ExportRouterOSWalledGardenView,
    HotspotWalledGardenDetailView,
    HotspotWalledGardenListView,
    PaymentSettingsView,
    PaymentSummaryMetricsView,
    PaymentTransactionDetailView,
    PaymentTransactionListView,
)
from apps.payments.api.webhook_views import SnippeWebhookView

urlpatterns = [
    # Transactions
    path('', PaymentTransactionListView.as_view(), name='payment-list'),
    path('<uuid:id>/', PaymentTransactionDetailView.as_view(), name='payment-detail'),
    path('reports/summary/', PaymentSummaryMetricsView.as_view(), name='payment-summary'),
    path('settings/', PaymentSettingsView.as_view(), name='payment-settings'),

    # Purchases
    path('purchases/', AccessPurchaseListView.as_view(), name='purchase-list'),
    path('purchases/<uuid:id>/', AccessPurchaseDetailView.as_view(), name='purchase-detail'),

    # Inbound Webhook
    path('snippe/webhook/', SnippeWebhookView.as_view(), name='snippe-webhook'),

    # Walled Garden
    path('walled-garden/', HotspotWalledGardenListView.as_view(), name='walled-garden-list'),
    path('walled-garden/<uuid:id>/', HotspotWalledGardenDetailView.as_view(), name='walled-garden-detail'),
    path('walled-garden/presets/apply/', ApplyWalledGardenPresetView.as_view(), name='walled-garden-preset-apply'),
    path('walled-garden/export-routeros/', ExportRouterOSWalledGardenView.as_view(), name='walled-garden-export-routeros'),
]
