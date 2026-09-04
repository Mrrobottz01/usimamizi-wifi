from django.urls import path

from .views import (
    ActivateEntitlementView,
    EntitlementDetailView,
    EntitlementListView,
    EntitlementReleaseDeviceView,
    ManualGrantView,
    ResumeEntitlementView,
    RevokeEntitlementView,
    SuspendEntitlementView,
)

urlpatterns = [
    path('', EntitlementListView.as_view(), name='entitlements-list'),
    path('manual-grant/', ManualGrantView.as_view(), name='entitlements-manual-grant'),
    path('<uuid:id>/', EntitlementDetailView.as_view(), name='entitlements-detail'),
    path('<uuid:id>/activate/', ActivateEntitlementView.as_view(), name='entitlements-activate'),
    path('<uuid:id>/suspend/', SuspendEntitlementView.as_view(), name='entitlements-suspend'),
    path('<uuid:id>/resume/', ResumeEntitlementView.as_view(), name='entitlements-resume'),
    path('<uuid:id>/revoke/', RevokeEntitlementView.as_view(), name='entitlements-revoke'),
    path('<uuid:id>/release-device/', EntitlementReleaseDeviceView.as_view(), name='entitlements-release-device'),
]
