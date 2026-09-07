from django.urls import path
from .views import (
    HealthCheckView,
    SystemWatchdogConfigView,
    SystemWatchdogStatusView,
    SystemWatchdogTestSMSView,
)

urlpatterns = [
    path('', HealthCheckView.as_view(), name='health-check'),
    path('watchdog/', SystemWatchdogStatusView.as_view(), name='watchdog-status'),
    path('watchdog/config/', SystemWatchdogConfigView.as_view(), name='watchdog-config'),
    path('watchdog/test-sms/', SystemWatchdogTestSMSView.as_view(), name='watchdog-test-sms'),
]
