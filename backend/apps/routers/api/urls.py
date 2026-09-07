from django.urls import path

from .views import (
    RouterBootstrapRscRawView,
    RouterBootstrapScriptView,
    RouterCredentialsView,
    RouterDetailView,
    RouterHealthView,
    RouterListCreateView,
    RouterProvisionView,
    RouterTestConnectionView,
)

app_name = 'routers'

urlpatterns = [
    path('', RouterListCreateView.as_view(), name='router-list-create'),
    path('<uuid:router_id>/', RouterDetailView.as_view(), name='router-detail'),
    path('<uuid:router_id>/credentials/', RouterCredentialsView.as_view(), name='router-credentials'),
    path('<uuid:router_id>/test-connection/', RouterTestConnectionView.as_view(), name='router-test-connection'),
    path('<uuid:router_id>/health/', RouterHealthView.as_view(), name='router-health'),
    path('<uuid:router_id>/refresh-health/', RouterHealthView.as_view(), name='router-refresh-health'),
    path('<uuid:router_id>/provision/', RouterProvisionView.as_view(), name='router-provision'),
    path('<uuid:router_id>/bootstrap-script/', RouterBootstrapScriptView.as_view(), name='router-bootstrap-script'),
    path('<uuid:router_id>/bootstrap.rsc', RouterBootstrapRscRawView.as_view(), name='router-bootstrap-rsc'),
]

