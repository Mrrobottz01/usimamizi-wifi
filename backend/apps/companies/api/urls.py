from django.urls import path

from .uplink_views import (
    RouterUplinkConnectView,
    RouterUplinkProfilesView,
    RouterUplinkRestoreHomeView,
    RouterUplinkScanView,
    RouterUplinkStatusView
)
from .views import CompanyDetailView, CompanyListView

urlpatterns = [
    path('', CompanyListView.as_view(), name='company-list'),
    path('<uuid:pk>/', CompanyDetailView.as_view(), name='company-detail'),
    path('uplink/status/', RouterUplinkStatusView.as_view(), name='company-uplink-status'),
    path('uplink/connect/', RouterUplinkConnectView.as_view(), name='company-uplink-connect'),
    path('uplink/scan/', RouterUplinkScanView.as_view(), name='company-uplink-scan'),
    path('uplink/restore-home/', RouterUplinkRestoreHomeView.as_view(), name='company-uplink-restore-home'),
    path('uplink/profiles/', RouterUplinkProfilesView.as_view(), name='company-uplink-profiles'),
    path('uplink/profiles/<uuid:profile_id>/', RouterUplinkProfilesView.as_view(), name='company-uplink-profile-detail'),
]

