from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.companies.permissions import IsCompanyMember
from apps.companies.selectors.company_selectors import get_company_by_id
from apps.companies.services.portal_services import (
    create_signed_portal_context,
    get_customer_error_message,
    get_default_hotspot,
    get_hotspot_login_url,
    get_or_create_default_hotspot,
    get_plans_for_hotspot,
    resolve_hotspot_by_slug,
    validate_and_redeem_portal_voucher,
    validate_destination_url,
    verify_signed_portal_context,
)
from apps.hotspot_sessions.models import HotspotSession, SessionStatus
from apps.payments.api.serializers import PublicPlanSerializer

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

        context_token = create_signed_portal_context(hotspot, request.query_params.dict())
        login_url = get_hotspot_login_url(hotspot, request.query_params.dict())

        serializer = PublicHotspotConfigSerializer(hotspot)
        data = serializer.data
        data['context_token'] = context_token
        data['login_url'] = login_url
        return Response(data, status=status.HTTP_200_OK)


class PublicHotspotPortalContextView(APIView):
    """
    POST /api/v1/public/hotspots/{slug}/portal-context/
    Initialize or refresh captive portal session context.
    Accepts runtime parameters sent by MikroTik HotSpot redirect:
      - link-login / link_login
      - link-orig / dst / link_orig
      - mac
      - ip
    Returns:
      - hotspot branding data
      - plans
      - validated login_url
      - gateway_ip
      - signed context_token
    """
    permission_classes = [AllowAny]

    def post(self, request, slug):
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

        raw_params = {}
        raw_params.update(request.query_params.dict())
        if isinstance(request.data, dict):
            raw_params.update(request.data)

        runtime_params = {
            'link-login': raw_params.get('link-login') or raw_params.get('link_login') or raw_params.get('link-login-only') or '',
            'link-orig': raw_params.get('link-orig') or raw_params.get('link_orig') or raw_params.get('dst') or '',
            'mac': raw_params.get('mac') or '',
            'ip': raw_params.get('ip') or '',
        }

        context_token = create_signed_portal_context(hotspot, runtime_params)
        login_url = get_hotspot_login_url(hotspot, runtime_params)

        plans = get_plans_for_hotspot(hotspot, include_inactive=False).order_by('price')
        plans_data = PublicPlanSerializer(plans, many=True).data

        hotspot_serializer = PublicHotspotConfigSerializer(hotspot)

        return Response({
            "hotspot": hotspot_serializer.data,
            "login_url": login_url,
            "gateway_ip": hotspot.gateway_ip or "",
            "context_token": context_token,
            "session_context": {
                "mac": (runtime_params.get('mac') or '').strip().upper(),
                "ip": (runtime_params.get('ip') or '').strip(),
                "link_orig": validate_destination_url(runtime_params.get('link-orig', '')),
                "gateway_ip": hotspot.gateway_ip or "",
            },
            "plans": plans_data,
        }, status=status.HTTP_200_OK)


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
        context_token = serializer.validated_data.get('context_token')
        link_login = serializer.validated_data.get('link_login')

        runtime_context = {}
        if context_token:
            decoded_context = verify_signed_portal_context(context_token, hotspot)
            if decoded_context:
                runtime_context.update(decoded_context)
        if link_login:
            runtime_context['link-login'] = link_login

        result = validate_and_redeem_portal_voucher(
            hotspot=hotspot,
            voucher_code=voucher_code,
            customer_phone=customer_phone,
            lang=language,
            runtime_context=runtime_context,
        )

        http_status = status.HTTP_200_OK if result.get("success") else status.HTTP_400_BAD_REQUEST
        return Response(result, status=http_status)


from django.utils import timezone
from apps.vouchers.models import Voucher

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

        clean_code = username.upper().replace('-', '').replace(' ', '')

        # Look up active session for this voucher username
        session = HotspotSession.objects.filter(
            company=hotspot.company,
            username__iexact=username
        ).order_by('-started_at').first()

        # Resolve entitlement from session or directly from voucher
        entitlement = session.entitlement if (session and session.entitlement) else None
        if not entitlement:
            voucher = Voucher.objects.filter(company=hotspot.company, code=clean_code).first()
            if voucher and hasattr(voucher, 'entitlement'):
                entitlement = voucher.entitlement

        now = timezone.now()
        remaining_seconds = None
        remaining_data_bytes = None
        if entitlement:
            if entitlement.expires_at:
                remaining_seconds = max(0, int((entitlement.expires_at - now).total_seconds()))
            if entitlement.data_limit_bytes is not None:
                remaining_data_bytes = max(0, entitlement.data_limit_bytes - entitlement.data_used_bytes)

        if not session:
            return Response({
                "connected": entitlement is not None and entitlement.status == 'ACTIVE',
                "status": "ACTIVE" if (entitlement and entitlement.status == 'ACTIVE') else "DISCONNECTED",
                "username": username,
                "plan_name": entitlement.plan.name if (entitlement and entitlement.plan) else "Access Plan",
                "remaining_seconds": remaining_seconds,
                "remaining_data_bytes": remaining_data_bytes,
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
            "remaining_seconds": remaining_seconds,
            "remaining_data_bytes": remaining_data_bytes,
        }, status=status.HTTP_200_OK)


class HotspotSettingsAdminView(APIView):
    """
    [LEGACY/DEPRECATED] GET, PUT /api/v1/settings/hotspot/?company_id={uuid}
    Admin endpoint to view and update default HotSpot branding and portal configuration.
    New integrations should use /api/v1/hotspots/ and /api/v1/hotspots/<id>/.
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

        hotspot = get_default_hotspot(company)
        if not hotspot:
            return Response({"code": "default_hotspot_not_configured", "detail": "No default hotspot configured for company."}, status=status.HTTP_404_NOT_FOUND)

        return Response(AdminHotspotSettingsSerializer(hotspot).data, status=status.HTTP_200_OK)

    def put(self, request):
        company_id = request.data.get('company_id') or request.query_params.get('company_id')
        if not company_id:
            return Response({"code": "missing_company_id", "detail": "'company_id' is required."}, status=status.HTTP_400_BAD_REQUEST)

        company = get_company_by_id(company_id)
        if not company:
            return Response({"code": "company_not_found", "detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, company)

        hotspot = get_default_hotspot(company)
        if not hotspot:
            hotspot = get_or_create_default_hotspot(company)

        serializer = AdminHotspotSettingsSerializer(hotspot, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)
