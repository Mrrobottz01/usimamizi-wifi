from django.urls import path

from .admin_views import (
    CustomerBlockView,
    CustomerDetailView,
    CustomerDeviceActionView,
    CustomerDevicesView,
    CustomerListCreateView,
    CustomerReactivateView,
    CustomerSubscriptionSettingsView,
    CustomerSubscriptionsView,
    CustomerSuspendView,
    CustomerTimelineView,
    SubscriptionDetailView,
    SubscriptionListCreateView,
    SubscriptionReactivateView,
    SubscriptionRenewView,
    SubscriptionSuspendView,
)
from .public_views import (
    CustomerPortalDevicesView,
    CustomerPortalDisconnectDeviceView,
    CustomerPortalMeView,
    CustomerPortalRenewView,
    CustomerPortalSubscriptionView,
    RequestCustomerOTPView,
    VerifyCustomerOTPView,
)

urlpatterns = [
    # Admin Customer Management
    path('customers/', CustomerListCreateView.as_view(), name='customer-list-create'),
    path('customers/<uuid:pk>/', CustomerDetailView.as_view(), name='customer-detail'),
    path('customers/<uuid:pk>/suspend/', CustomerSuspendView.as_view(), name='customer-suspend'),
    path('customers/<uuid:pk>/reactivate/', CustomerReactivateView.as_view(), name='customer-reactivate'),
    path('customers/<uuid:pk>/block/', CustomerBlockView.as_view(), name='customer-block'),
    path('customers/<uuid:pk>/devices/', CustomerDevicesView.as_view(), name='customer-devices'),
    path('customers/<uuid:pk>/devices/<uuid:device_id>/<str:action>/', CustomerDeviceActionView.as_view(), name='customer-device-action'),
    path('customers/<uuid:pk>/subscriptions/', CustomerSubscriptionsView.as_view(), name='customer-subscriptions'),
    path('customers/<uuid:pk>/timeline/', CustomerTimelineView.as_view(), name='customer-timeline'),

    # Admin Subscription Management
    path('subscriptions/', SubscriptionListCreateView.as_view(), name='subscription-list-create'),
    path('subscriptions/<uuid:pk>/', SubscriptionDetailView.as_view(), name='subscription-detail'),
    path('subscriptions/<uuid:pk>/renew/', SubscriptionRenewView.as_view(), name='subscription-renew'),
    path('subscriptions/<uuid:pk>/suspend/', SubscriptionSuspendView.as_view(), name='subscription-suspend'),
    path('subscriptions/<uuid:pk>/reactivate/', SubscriptionReactivateView.as_view(), name='subscription-reactivate'),

    # Tenant Subscription Settings
    path('settings/subscriptions/', CustomerSubscriptionSettingsView.as_view(), name='customer-subscription-settings'),

    # Customer Self-Service Portal Public Endpoints
    path('public/customer/request-otp/', RequestCustomerOTPView.as_view(), name='customer-portal-request-otp'),
    path('public/customer/verify-otp/', VerifyCustomerOTPView.as_view(), name='customer-portal-verify-otp'),
    path('public/customer/me/', CustomerPortalMeView.as_view(), name='customer-portal-me'),
    path('public/customer/subscription/', CustomerPortalSubscriptionView.as_view(), name='customer-portal-subscription'),
    path('public/customer/renew/', CustomerPortalRenewView.as_view(), name='customer-portal-renew'),
    path('public/customer/devices/', CustomerPortalDevicesView.as_view(), name='customer-portal-devices'),
    path('public/customer/disconnect-device/', CustomerPortalDisconnectDeviceView.as_view(), name='customer-portal-disconnect-device'),
]
