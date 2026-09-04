from django.urls import path

from .views import PlanDetailView, PlanListCreateView

urlpatterns = [
    path('', PlanListCreateView.as_view(), name='plan-list-create'),
    path('<uuid:plan_id>/', PlanDetailView.as_view(), name='plan-detail'),
]
