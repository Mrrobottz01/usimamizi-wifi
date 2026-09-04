from django.urls import path

from .public_views import (
    PublicHotspotPortalConfigView,
    PublicHotspotStatusView,
    PublicHotspotVoucherRedeemView,
)

urlpatterns = [
    path('<slug:slug>/portal/', PublicHotspotPortalConfigView.as_view(), name='public-hotspot-portal'),
    path('<slug:slug>/voucher/', PublicHotspotVoucherRedeemView.as_view(), name='public-hotspot-voucher'),
    path('<slug:slug>/status/', PublicHotspotStatusView.as_view(), name='public-hotspot-status'),
]
