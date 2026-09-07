from django.urls import path
from .views import (
    LocationDetailView,
    LocationHotspotsView,
    LocationListCreateView,
    LocationMoveRouterView,
    LocationReactivateView,
    LocationRoutersView,
    LocationSessionsView,
)

urlpatterns = [
    path('', LocationListCreateView.as_view(), name='location-list-create'),
    path('<uuid:location_id>/', LocationDetailView.as_view(), name='location-detail'),
    path('<uuid:location_id>/reactivate/', LocationReactivateView.as_view(), name='location-reactivate'),
    path('<uuid:location_id>/routers/', LocationRoutersView.as_view(), name='location-routers'),
    path('<uuid:location_id>/hotspots/', LocationHotspotsView.as_view(), name='location-hotspots'),
    path('<uuid:location_id>/sessions/', LocationSessionsView.as_view(), name='location-sessions'),
    path('<uuid:location_id>/move-router/', LocationMoveRouterView.as_view(), name='location-move-router'),
]