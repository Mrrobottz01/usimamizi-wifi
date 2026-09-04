from django.urls import path

from .views import (
    HotspotSessionDetailView,
    HotspotSessionListView,
    SessionDisconnectHistoryView,
    SessionDisconnectView,
)

urlpatterns = [
    path('', HotspotSessionListView.as_view(), name='sessions-list'),
    path('<uuid:id>/', HotspotSessionDetailView.as_view(), name='sessions-detail'),
    path('<uuid:id>/disconnect/', SessionDisconnectView.as_view(), name='sessions-disconnect'),
    path('<uuid:id>/disconnect-history/', SessionDisconnectHistoryView.as_view(), name='sessions-disconnect-history'),
]
