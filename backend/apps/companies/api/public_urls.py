from django.urls import path

from .public_views import (
    PublicHotspotPortalConfigView,
    PublicHotspotPortalContextView,
    PublicHotspotStatusView,
    PublicHotspotVoucherRedeemView,
)

urlpatterns = [
    path('<slug:slug>/portal/', PublicHotspotPortalConfigView.as_view(), name='public-hotspot-portal'),
    path('<slug:slug>/portal-context/', PublicHotspotPortalContextView.as_view(), name='public-hotspot-portal-context'),
    path('<slug:slug>/voucher/', PublicHotspotVoucherRedeemView.as_view(), name='public-hotspot-voucher'),
    path('<slug:slug>/status/', PublicHotspotStatusView.as_view(), name='public-hotspot-status'),
]
