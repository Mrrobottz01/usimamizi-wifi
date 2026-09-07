from django.urls import path
from .anti_tethering_views import (
    HotspotAntiTetheringDetailView,
    HotspotAntiTetheringSyncView,
    HotspotAntiTetheringStatusView,
    HotspotAntiTetheringCountersView,
    HotspotAntiTetheringRestoreDefaultsView,
)
from .hotspot_views import (
    HotspotDetailView,
    HotspotListCreateView,
    HotspotPlansView,
    HotspotSetDefaultView,
)

urlpatterns = [
    path('', HotspotListCreateView.as_view(), name='hotspot-list-create'),
    path('<uuid:hotspot_id>/', HotspotDetailView.as_view(), name='hotspot-detail'),
    path('<uuid:hotspot_id>/set-default/', HotspotSetDefaultView.as_view(), name='hotspot-set-default'),
    path('<uuid:hotspot_id>/plans/', HotspotPlansView.as_view(), name='hotspot-plans'),
    path('<str:hotspot_id>/anti-tethering/', HotspotAntiTetheringDetailView.as_view(), name='hotspot-anti-tethering-detail'),
    path('<str:hotspot_id>/anti-tethering/sync/', HotspotAntiTetheringSyncView.as_view(), name='hotspot-anti-tethering-sync'),
    path('<str:hotspot_id>/anti-tethering/status/', HotspotAntiTetheringStatusView.as_view(), name='hotspot-anti-tethering-status'),
    path('<str:hotspot_id>/anti-tethering/counters/', HotspotAntiTetheringCountersView.as_view(), name='hotspot-anti-tethering-counters'),
    path('<str:hotspot_id>/anti-tethering/restore-defaults/', HotspotAntiTetheringRestoreDefaultsView.as_view(), name='hotspot-anti-tethering-restore-defaults'),
]
