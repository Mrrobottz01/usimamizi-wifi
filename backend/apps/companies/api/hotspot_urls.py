from django.urls import path
from .anti_tethering_views import (
    HotspotAntiTetheringDetailView,
    HotspotAntiTetheringSyncView,
    HotspotAntiTetheringStatusView,
    HotspotAntiTetheringCountersView,
    HotspotAntiTetheringRestoreDefaultsView,
)

urlpatterns = [
    path('<str:hotspot_id>/anti-tethering/', HotspotAntiTetheringDetailView.as_view(), name='hotspot-anti-tethering-detail'),
    path('<str:hotspot_id>/anti-tethering/sync/', HotspotAntiTetheringSyncView.as_view(), name='hotspot-anti-tethering-sync'),
    path('<str:hotspot_id>/anti-tethering/status/', HotspotAntiTetheringStatusView.as_view(), name='hotspot-anti-tethering-status'),
    path('<str:hotspot_id>/anti-tethering/counters/', HotspotAntiTetheringCountersView.as_view(), name='hotspot-anti-tethering-counters'),
    path('<str:hotspot_id>/anti-tethering/restore-defaults/', HotspotAntiTetheringRestoreDefaultsView.as_view(), name='hotspot-anti-tethering-restore-defaults'),
]
