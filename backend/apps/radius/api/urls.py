from django.urls import path

from .views import RadiusAccountingView, RadiusAuthorizeView

urlpatterns = [
    path('authorize/', RadiusAuthorizeView.as_view(), name='radius-authorize'),
    path('accounting/', RadiusAccountingView.as_view(), name='radius-accounting'),
]
