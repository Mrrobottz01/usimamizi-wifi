import logging
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.companies.models import Company, HotspotConfiguration
from apps.companies.selectors.company_selectors import get_company_by_id
from apps.companies.services.portal_services import get_plans_for_hotspot
from apps.plans.models import Plan
from .hotspot_serializers import (
    HotspotCreateUpdateSerializer,
    HotspotDetailSerializer,
    HotspotListSerializer,
    HotspotPlanSummarySerializer,
)

logger = logging.getLogger(__name__)


def _get_request_company(request) -> Optional[Company]:
    company_id = None
    if request.method == 'GET':
        company_id = request.query_params.get('company_id')
    elif hasattr(request, 'data') and isinstance(request.data, dict):
        company_id = request.data.get('company_id') or request.query_params.get('company_id')

    if company_id:
        c = get_company_by_id(company_id)
        if c:
            return c

    c = Company.objects.filter(memberships__user=request.user, memberships__is_active=True).first()
    if not c:
        c = Company.objects.first()
    return c


class HotspotListCreateView(APIView):
    """
    GET  /api/v1/hotspots/ — List hotspots for company with optional filters
    POST /api/v1/hotspots/ — Create a new hotspot configuration
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = _get_request_company(request)
        if not company:
            return Response({'detail': 'Company not found.'}, status=status.HTTP_404_NOT_FOUND)

        qs = HotspotConfiguration.objects.filter(company=company).select_related('location', 'router').prefetch_related('plans')

        # Filter by router
        router_id = request.query_params.get('router')
        if router_id:
            qs = qs.filter(router_id=router_id)

        # Filter by location
        location_id = request.query_params.get('location')
        if location_id:
            qs = qs.filter(location_id=location_id)

        # Filter by is_active
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')

        serializer = HotspotListSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        company = _get_request_company(request)
        if not company:
            return Response({'detail': 'Company not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = HotspotCreateUpdateSerializer(data=request.data, context={'company': company})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            hotspot = serializer.save()
            return Response(HotspotDetailSerializer(hotspot).data, status=status.HTTP_201_CREATED)
        except ValidationError as exc:
            return Response({'detail': exc.message_dict if hasattr(exc, 'message_dict') else str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class HotspotDetailView(APIView):
    """
    GET    /api/v1/hotspots/<id>/ — Retrieve hotspot details
    PATCH  /api/v1/hotspots/<id>/ — Update hotspot configuration
    DELETE /api/v1/hotspots/<id>/ — Deactivate or delete hotspot
    """
    permission_classes = [IsAuthenticated]

    def _get_hotspot(self, hotspot_id, request) -> Optional[HotspotConfiguration]:
        company = _get_request_company(request)
        if not company:
            return None
        return HotspotConfiguration.objects.filter(id=hotspot_id, company=company).select_related('location', 'router').prefetch_related('plans').first()

    def get(self, request, hotspot_id):
        hotspot = self._get_hotspot(hotspot_id, request)
        if not hotspot:
            return Response({'detail': 'HotSpot not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(HotspotDetailSerializer(hotspot).data)

    def patch(self, request, hotspot_id):
        hotspot = self._get_hotspot(hotspot_id, request)
        if not hotspot:
            return Response({'detail': 'HotSpot not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = HotspotCreateUpdateSerializer(hotspot, data=request.data, partial=True, context={'company': hotspot.company})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            updated = serializer.save()
            return Response(HotspotDetailSerializer(updated).data)
        except ValidationError as exc:
            return Response({'detail': exc.message_dict if hasattr(exc, 'message_dict') else str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, hotspot_id):
        hotspot = self._get_hotspot(hotspot_id, request)
        if not hotspot:
            return Response({'detail': 'HotSpot not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Safety: check linked purchases or sessions
        linked_purchases = getattr(hotspot, 'purchases', None).count() if hasattr(hotspot, 'purchases') else 0
        linked_sessions = getattr(hotspot, 'sessions', None).count() if hasattr(hotspot, 'sessions') else 0

        if linked_purchases > 0 or linked_sessions > 0:
            hotspot.is_active = False
            hotspot.save(update_fields=['is_active', 'updated_at'])
            return Response({
                'action': 'deactivated',
                'detail': f"HotSpot '{hotspot.name}' has active history ({linked_purchases} purchase(s), {linked_sessions} session(s)) and was deactivated rather than deleted."
            }, status=status.HTTP_200_OK)

        hotspot.delete()
        return Response({'action': 'deleted', 'detail': f"HotSpot '{hotspot.name}' deleted."}, status=status.HTTP_200_OK)


class HotspotSetDefaultView(APIView):
    """
    POST /api/v1/hotspots/<id>/set-default/ — Designate hotspot as primary default for company
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, hotspot_id):
        company = _get_request_company(request)
        hotspot = get_object_or_404(HotspotConfiguration, id=hotspot_id, company=company)

        # Unset all other defaults for company
        HotspotConfiguration.objects.filter(company=company, is_default=True).exclude(id=hotspot.id).update(is_default=False)
        hotspot.is_default = True
        hotspot.save(update_fields=['is_default', 'updated_at'])

        return Response({
            'detail': f"HotSpot '{hotspot.name}' is now the default hotspot for {company.name}.",
            'hotspot_id': str(hotspot.id),
            'is_default': True,
        }, status=status.HTTP_200_OK)


class HotspotPlansView(APIView):
    """
    GET  /api/v1/hotspots/<id>/plans/ — List plans available on this hotspot
    POST /api/v1/hotspots/<id>/plans/ — Assign plans to this hotspot
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, hotspot_id):
        company = _get_request_company(request)
        hotspot = get_object_or_404(HotspotConfiguration, id=hotspot_id, company=company)

        plans = get_plans_for_hotspot(hotspot)
        serializer = HotspotPlanSummarySerializer(plans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, hotspot_id):
        company = _get_request_company(request)
        hotspot = get_object_or_404(HotspotConfiguration, id=hotspot_id, company=company)

        plan_ids = request.data.get('plan_ids', [])
        if not isinstance(plan_ids, list):
            return Response({'detail': "'plan_ids' must be a list of UUIDs."}, status=status.HTTP_400_BAD_REQUEST)

        plans = Plan.objects.filter(company=company, id__in=plan_ids)
        hotspot.plans.set(plans)

        updated_plans = get_plans_for_hotspot(hotspot)
        return Response({
            'detail': f"Assigned {plans.count()} plan(s) to hotspot '{hotspot.name}'.",
            'plans_count': plans.count(),
            'plans': HotspotPlanSummarySerializer(updated_plans, many=True).data,
        }, status=status.HTTP_200_OK)
