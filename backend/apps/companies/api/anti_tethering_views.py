import logging
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditLog
from ..models import HotspotConfiguration
from ..permissions import IsCompanyMember
from ..selectors.company_selectors import get_company_by_id
from ..services.portal_services import get_or_create_default_hotspot
from ..services.anti_tethering_services import (
    get_or_create_anti_tethering_policy,
    get_anti_tethering_status,
    get_anti_tethering_counters,
    sync_anti_tethering_policy,
    restore_default_anti_tethering_policy,
)
from .anti_tethering_serializers import AntiTetheringPolicySerializer

logger = logging.getLogger(__name__)


def resolve_hotspot_from_request(request, hotspot_id=None) -> tuple:
    """
    Resolve HotspotConfiguration from either path param (UUID or 'default')
    or company_id query parameter.
    """
    if hotspot_id and str(hotspot_id).lower() != 'default':
        try:
            hotspot = HotspotConfiguration.objects.select_related('company').get(id=hotspot_id)
            return hotspot, None
        except (HotspotConfiguration.DoesNotExist, ValueError):
            return None, Response(
                {"code": "hotspot_not_found", "detail": "HotSpot not found."},
                status=status.HTTP_404_NOT_FOUND
            )

    company_id = request.query_params.get('company_id') or (request.data.get('company_id') if hasattr(request, 'data') else None)
    if not company_id:
        return None, Response(
            {"code": "missing_company_id", "detail": "'company_id' query parameter is required when hotspot is default."},
            status=status.HTTP_400_BAD_REQUEST
        )

    company = get_company_by_id(company_id)
    if not company:
        return None, Response(
            {"code": "company_not_found", "detail": "Company not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    hotspot = get_or_create_default_hotspot(company)
    return hotspot, None


class HotspotAntiTetheringDetailView(APIView):
    """
    GET, PATCH /api/v1/hotspots/{hotspot_id}/anti-tethering/
    View and update anti-tethering configuration for a hotspot.
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get(self, request, hotspot_id):
        hotspot, err_resp = resolve_hotspot_from_request(request, hotspot_id)
        if err_resp:
            return err_resp

        self.check_object_permissions(request, hotspot.company)
        policy = get_or_create_anti_tethering_policy(hotspot)
        serializer = AntiTetheringPolicySerializer(policy)

        # Include live router status check
        router_status = get_anti_tethering_status(hotspot)

        return Response({
            **serializer.data,
            'router_status': router_status,
        }, status=status.HTTP_200_OK)

    def patch(self, request, hotspot_id):
        hotspot, err_resp = resolve_hotspot_from_request(request, hotspot_id)
        if err_resp:
            return err_resp

        self.check_object_permissions(request, hotspot.company)
        policy = get_or_create_anti_tethering_policy(hotspot)

        old_data = AntiTetheringPolicySerializer(policy).data
        serializer = AntiTetheringPolicySerializer(policy, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        updated_policy = serializer.save()

        # Audit Log
        AuditLog.objects.create(
            company=hotspot.company,
            user=request.user,
            action='ANTI_TETHERING_POLICY_UPDATED',
            resource_type='HotspotConfiguration',
            resource_id=str(hotspot.id),
            changes={
                'before': old_data,
                'after': serializer.data,
            }
        )

        # Auto-sync to router if enabled or requested
        sync_requested = request.query_params.get('sync', 'true').lower() in ('true', '1')
        sync_result = None
        if sync_requested:
            sync_result = sync_anti_tethering_policy(hotspot, user=request.user)

        router_status = get_anti_tethering_status(hotspot)

        return Response({
            **serializer.data,
            'router_status': router_status,
            'sync_result': sync_result,
        }, status=status.HTTP_200_OK)


class HotspotAntiTetheringSyncView(APIView):
    """
    POST /api/v1/hotspots/{hotspot_id}/anti-tethering/sync/
    Force reconciliation between SaaS policy and RouterOS firewall rules.
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def post(self, request, hotspot_id):
        hotspot, err_resp = resolve_hotspot_from_request(request, hotspot_id)
        if err_resp:
            return err_resp

        self.check_object_permissions(request, hotspot.company)
        sync_result = sync_anti_tethering_policy(hotspot, user=request.user)

        http_status = status.HTTP_200_OK if sync_result.get('success') else status.HTTP_502_BAD_GATEWAY
        return Response(sync_result, status=http_status)


class HotspotAntiTetheringStatusView(APIView):
    """
    GET /api/v1/hotspots/{hotspot_id}/anti-tethering/status/
    Query live status of anti-tethering rules on RouterOS.
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get(self, request, hotspot_id):
        hotspot, err_resp = resolve_hotspot_from_request(request, hotspot_id)
        if err_resp:
            return err_resp

        self.check_object_permissions(request, hotspot.company)
        live_status = get_anti_tethering_status(hotspot)
        return Response(live_status, status=status.HTTP_200_OK)


class HotspotAntiTetheringCountersView(APIView):
    """
    GET /api/v1/hotspots/{hotspot_id}/anti-tethering/counters/
    Query real-time packet and byte counters for anti-tethering rules.
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get(self, request, hotspot_id):
        hotspot, err_resp = resolve_hotspot_from_request(request, hotspot_id)
        if err_resp:
            return err_resp

        self.check_object_permissions(request, hotspot.company)
        counters = get_anti_tethering_counters(hotspot)
        return Response(counters, status=status.HTTP_200_OK)


class HotspotAntiTetheringRestoreDefaultsView(APIView):
    """
    POST /api/v1/hotspots/{hotspot_id}/anti-tethering/restore-defaults/
    Restore recommended baseline settings and sync immediately with router.
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def post(self, request, hotspot_id):
        hotspot, err_resp = resolve_hotspot_from_request(request, hotspot_id)
        if err_resp:
            return err_resp

        self.check_object_permissions(request, hotspot.company)
        result = restore_default_anti_tethering_policy(hotspot, user=request.user)
        return Response(result, status=status.HTTP_200_OK)
