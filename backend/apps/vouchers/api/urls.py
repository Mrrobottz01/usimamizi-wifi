from django.urls import path

from .views import (
    BatchPrintableCardsView,
    ExportBatchCSVView,
    ExportRouterOSScriptView,
    ReserveVoucherView,
    RevokeVoucherView,
    SendVoucherSMSView,
    VoucherBatchDetailView,
    VoucherBatchListCreateView,
    VoucherListView,
    VoucherMetricsView,
    VoucherTimelineView,
)

urlpatterns = [
    path('voucher-batches/', VoucherBatchListCreateView.as_view(), name='voucher-batch-list-create'),
    path('voucher-batches/<uuid:batch_id>/', VoucherBatchDetailView.as_view(), name='voucher-batch-detail'),
    path('voucher-batches/<uuid:batch_id>/export-routeros/', ExportRouterOSScriptView.as_view(), name='export-routeros-script'),
    path('voucher-batches/<uuid:batch_id>/export-csv/', ExportBatchCSVView.as_view(), name='export-batch-csv'),
    path('voucher-batches/<uuid:batch_id>/print/', BatchPrintableCardsView.as_view(), name='export-batch-print'),
    path('vouchers/', VoucherListView.as_view(), name='voucher-list'),
    path('vouchers/metrics/', VoucherMetricsView.as_view(), name='voucher-metrics'),
    path('vouchers/<uuid:voucher_id>/timeline/', VoucherTimelineView.as_view(), name='voucher-timeline'),
    path('vouchers/<uuid:voucher_id>/send-sms/', SendVoucherSMSView.as_view(), name='voucher-send-sms'),
    path('vouchers/<uuid:voucher_id>/reserve/', ReserveVoucherView.as_view(), name='voucher-reserve'),
    path('vouchers/<uuid:voucher_id>/revoke/', RevokeVoucherView.as_view(), name='voucher-revoke'),
]

