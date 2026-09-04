from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.companies.permissions import IsCompanyMember
from apps.companies.selectors.company_selectors import get_company_by_id
from apps.companies.services.portal_services import (
    get_customer_error_message,
    get_or_create_default_hotspot,
    resolve_hotspot_by_slug,
    validate_and_redeem_portal_voucher,
)
from apps.hotspot_sessions.models import HotspotSession, SessionStatus

from .public_serializers import (
    AdminHotspotSettingsSerializer,
    PublicHotspotConfigSerializer,
    PublicVoucherSubmitSerializer,
)


class PublicHotspotPortalConfigView(APIView):
    """
    GET /api/v1/public/hotspots/{slug}/portal/
    Fetch public branding tokens for a captive portal instance by slug.
    Unauthenticated endpoint for captive portal clients.
    """
    permission_classes = [AllowAny]

    def get(self, request, slug):
        hotspot = resolve_hotspot_by_slug(slug)
        if not hotspot:
            return Response({
                "code": "HOTSPOT_NOT_FOUND",
                "detail": "Wi-Fi HotSpot configuration not found."
            }, status=status.HTTP_404_NOT_FOUND)

        if not hotspot.is_active:
            return Response({
                "code": "HOTSPOT_INACTIVE",
                "detail": "This Wi-Fi HotSpot is currently disabled."
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = PublicHotspotConfigSerializer(hotspot)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PublicHotspotVoucherRedeemView(APIView):
    """
    POST /api/v1/public/hotspots/{slug}/voucher/
    Validate and redeem a customer voucher on the public captive portal.
    Atomically redeems available vouchers or checks existing redeemed access.
    """
    permission_classes = [AllowAny]

    def post(self, request, slug):
        hotspot = resolve_hotspot_by_slug(slug)
        if not hotspot:
            return Response({
                "success": False,
                "error_code": "HOTSPOT_NOT_FOUND",
                "message": get_customer_error_message("NOT_FOUND", "EN")
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = PublicVoucherSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        voucher_code = serializer.validated_data['voucher_code']
        customer_phone = serializer.validated_data.get('customer_phone')
        language = serializer.validated_data.get('language', hotspot.default_language or 'EN')

        result = validate_and_redeem_portal_voucher(
            hotspot=hotspot,
            voucher_code=voucher_code,
            customer_phone=customer_phone,
            lang=language
        )

        http_status = status.HTTP_200_OK if result.get("success") else status.HTTP_400_BAD_REQUEST
        return Response(result, status=http_status)


class PublicHotspotStatusView(APIView):
    """
    GET /api/v1/public/hotspots/{slug}/status/?username={voucher_code}
    Query connection status for a client on the public captive portal.
    """
    permission_classes = [AllowAny]

    def get(self, request, slug):
        hotspot = resolve_hotspot_by_slug(slug)
        if not hotspot:
            return Response({"code": "not_found", "detail": "HotSpot not found."}, status=status.HTTP_404_NOT_FOUND)

        username = request.query_params.get('username', '').strip()
        if not username:
            return Response({"code": "missing_username", "detail": "'username' parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Look up active session for this voucher username
        session = HotspotSession.objects.filter(
            company=hotspot.company,
            username__iexact=username
        ).order_by('-started_at').first()

        if not session:
            return Response({
                "connected": False,
                "status": "DISCONNECTED",
                "username": username,
            }, status=status.HTTP_200_OK)

        return Response({
            "connected": session.status == SessionStatus.ACTIVE,
            "status": session.status,
            "username": session.username,
            "mac_address": session.mac_address,
            "plan_name": session.entitlement.plan.name if session.entitlement and session.entitlement.plan else "Access Plan",
            "session_seconds": session.session_seconds,
            "total_bytes": session.total_bytes,
            "input_bytes": session.input_bytes,
            "output_bytes": session.output_bytes,
            "started_at": session.started_at,
        }, status=status.HTTP_200_OK)


class HotspotSettingsAdminView(APIView):
    """
    GET, PUT /api/v1/settings/hotspot/?company_id={uuid}
    Admin endpoint to view and update HotSpot branding and portal configuration.
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get(self, request):
        company_id = request.query_params.get('company_id')
        if not company_id:
            return Response({"code": "missing_company_id", "detail": "'company_id' is required."}, status=status.HTTP_400_BAD_REQUEST)

        company = get_company_by_id(company_id)
        if not company:
            return Response({"code": "company_not_found", "detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, company)

        hotspot = get_or_create_default_hotspot(company)
        return Response(AdminHotspotSettingsSerializer(hotspot).data, status=status.HTTP_200_OK)

    def put(self, request):
        company_id = request.data.get('company_id') or request.query_params.get('company_id')
        if not company_id:
            return Response({"code": "missing_company_id", "detail": "'company_id' is required."}, status=status.HTTP_400_BAD_REQUEST)

        company = get_company_by_id(company_id)
        if not company:
            return Response({"code": "company_not_found", "detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, company)

        hotspot = get_or_create_default_hotspot(company)
        serializer = AdminHotspotSettingsSerializer(hotspot, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)
