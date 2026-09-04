from django.urls import path

from apps.payments.api.public_views import (
    PublicHotspotPlansView,
    PublicInitiatePurchaseView,
    PublicPurchaseStatusView,
)

urlpatterns = [
    path('hotspots/<slug:slug>/plans/', PublicHotspotPlansView.as_view(), name='public-hotspot-plans'),
    path('hotspots/<slug:slug>/purchases/', PublicInitiatePurchaseView.as_view(), name='public-hotspot-purchase-initiate'),
    path('purchases/<str:reference>/status/', PublicPurchaseStatusView.as_view(), name='public-purchase-status'),
]
