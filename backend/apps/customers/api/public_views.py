import logging
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.companies.models import HotspotConfiguration
from apps.hotspot_sessions.models import HotspotSession, SessionDisconnectTrigger, SessionStatus
from apps.hotspot_sessions.services.session_control import disconnect_hotspot_session
from apps.payments.services.purchase_services import initiate_access_purchase
from apps.plans.models import Plan
from .serializers import (
    CustomerDeviceSerializer,
    CustomerSerializer,
    SubscriptionSerializer,
)
from ..models import (
    Customer,
    CustomerStatus,
    Subscription,
    SubscriptionStatus,
)
from ..services.customer_services import normalize_customer_phone
from ..services.otp_services import (
    authenticate_customer_token,
    generate_and_send_customer_otp,
    verify_customer_otp,
)

logger = logging.getLogger(__name__)


def _get_portal_customer(request) -> Customer | None:
    """
    Extracts and authenticates Customer from Authorization: Bearer <token>.
    """
    auth_header = (
        request.headers.get('Authorization')
        or request.META.get('HTTP_AUTHORIZATION')
        or ''
    )
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header.split(' ')[1].strip()
    return authenticate_customer_token(token)


class RequestCustomerOTPView(APIView):
    """
    POST /api/v1/public/customer/request-otp/
    Body: { "phone": "0712345678", "slug": "default" }
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get('phone', '').strip()
        slug = request.data.get('slug', '').strip()

        if not phone:
            return Response(
                {"code": "missing_phone", "detail": "Phone number is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        hotspot = None
        company = None
        if slug:
            hotspot = HotspotConfiguration.objects.filter(slug=slug, is_active=True).first()
            if hotspot:
                company = hotspot.company

        if not company:
            # Fallback to first active hotspot or company
            hotspot = HotspotConfiguration.objects.filter(is_active=True).first()
            if hotspot:
                company = hotspot.company

        if not company:
            return Response(
                {"code": "hotspot_not_found", "detail": "Invalid portal location."},
                status=status.HTTP_404_NOT_FOUND,
            )

        success, message, cooldown = generate_and_send_customer_otp(
            company=company,
            phone=phone,
            hotspot=hotspot,
        )

        if not success:
            return Response(
                {"code": "otp_failed", "detail": message, "cooldown_remaining": cooldown},
                status=status.HTTP_429_TOO_MANY_REQUESTS if cooldown else status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            "code": "otp_sent",
            "detail": message,
            "normalized_phone": normalize_customer_phone(phone),
        }, status=status.HTTP_200_OK)


class VerifyCustomerOTPView(APIView):
    """
    POST /api/v1/public/customer/verify-otp/
    Body: { "phone": "0712345678", "code": "123456", "slug": "default" }
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get('phone', '').strip()
        code = request.data.get('code', '').strip()
        slug = request.data.get('slug', '').strip()

        if not phone or not code:
            return Response(
                {"code": "missing_fields", "detail": "Phone number and code are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        hotspot = None
        company = None
        if slug:
            hotspot = HotspotConfiguration.objects.filter(slug=slug, is_active=True).first()
            if hotspot:
                company = hotspot.company

        if not company:
            hotspot = HotspotConfiguration.objects.filter(is_active=True).first()
            if hotspot:
                company = hotspot.company

        if not company:
            return Response(
                {"code": "hotspot_not_found", "detail": "Invalid portal location."},
                status=status.HTTP_404_NOT_FOUND,
            )

        success, message, customer, token = verify_customer_otp(
            company=company,
            phone=phone,
            code=code,
        )

        if not success:
            return Response(
                {"code": "verify_failed", "detail": message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            "code": "verified",
            "token": token,
            "customer": CustomerSerializer(customer).data,
            "hotspot_name": hotspot.brand_name if hotspot else company.name,
        }, status=status.HTTP_200_OK)


class CustomerPortalMeView(APIView):
    """
    GET /api/v1/public/customer/me/
    Header: Authorization: Bearer <token>
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        customer = _get_portal_customer(request)
        if not customer:
            return Response(
                {"code": "unauthorized", "detail": "Invalid or expired session."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        data = CustomerSerializer(customer).data
        data['company_name'] = customer.company.name
        return Response(data, status=status.HTTP_200_OK)


class CustomerPortalSubscriptionView(APIView):
    """
    GET /api/v1/public/customer/subscription/
    Header: Authorization: Bearer <token>
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        customer = _get_portal_customer(request)
        if not customer:
            return Response(
                {"code": "unauthorized", "detail": "Invalid or expired session."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Get active or grace subscription first, else most recent
        sub = customer.subscriptions.filter(
            status__in=[SubscriptionStatus.ACTIVE, SubscriptionStatus.GRACE]
        ).order_by('-current_period_end').first()

        if not sub:
            sub = customer.subscriptions.order_by('-created_at').first()

        if not sub:
            return Response({"subscription": None}, status=status.HTTP_200_OK)

        return Response({
            "subscription": SubscriptionSerializer(sub).data
        }, status=status.HTTP_200_OK)


class CustomerPortalRenewView(APIView):
    """
    POST /api/v1/public/customer/renew/
    Header: Authorization: Bearer <token>
    Body: { "plan_id": "<uuid>", "payment_method": "AIRTEL_MONEY" }
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        customer = _get_portal_customer(request)
        if not customer:
            return Response(
                {"code": "unauthorized", "detail": "Invalid or expired session."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        plan_id = request.data.get('plan_id')
        payment_method = request.data.get('payment_method', 'MPESA')
        client_mac = request.data.get('client_mac', '')

        # If plan_id is omitted, try renewing current active plan
        if not plan_id:
            active_sub = customer.subscriptions.filter(
                status__in=[SubscriptionStatus.ACTIVE, SubscriptionStatus.GRACE]
            ).first()
            if active_sub:
                plan_id = active_sub.plan_id

        if not plan_id:
            return Response(
                {"code": "missing_plan", "detail": "Plan selection is required to renew."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            plan = Plan.objects.get(pk=plan_id, company=customer.company, is_active=True)
        except Plan.DoesNotExist:
            return Response(
                {"code": "plan_not_found", "detail": "Selected plan is unavailable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Initiate purchase via Snippe
        hotspot = customer.company.hotspots.filter(is_active=True).first()
        purchase, transaction_obj, api_result = initiate_access_purchase(
            company=customer.company,
            hotspot=hotspot,
            plan=plan,
            customer_phone=customer.normalized_phone,
            client_mac=client_mac,
        )

        return Response({
            "code": "payment_initiated",
            "purchase_reference": purchase.reference,
            "internal_reference": transaction_obj.internal_reference if transaction_obj else None,
            "status": transaction_obj.status if transaction_obj else "PENDING",
            "instructions": "Please enter your mobile money PIN when prompted on your phone.",
            "api_result": api_result,
        }, status=status.HTTP_200_OK)


class CustomerPortalDevicesView(APIView):
    """
    GET /api/v1/public/customer/devices/
    Header: Authorization: Bearer <token>
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        customer = _get_portal_customer(request)
        if not customer:
            return Response(
                {"code": "unauthorized", "detail": "Invalid or expired session."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        devices = customer.devices.all().order_by('-last_seen_at')
        return Response(CustomerDeviceSerializer(devices, many=True).data, status=status.HTTP_200_OK)


class CustomerPortalDisconnectDeviceView(APIView):
    """
    POST /api/v1/public/customer/disconnect-device/
    Header: Authorization: Bearer <token>
    Body: { "mac_address": "AA:BB:CC:DD:EE:FF" }
    Disconnects the active session for the given MAC address via RFC 3576 POD.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        customer = _get_portal_customer(request)
        if not customer:
            return Response(
                {"code": "unauthorized", "detail": "Invalid or expired session."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        mac = request.data.get('mac_address', '').strip().upper()
        if not mac:
            return Response(
                {"code": "missing_mac", "detail": "MAC address is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Disconnect active sessions matching this MAC
        active_sessions = HotspotSession.objects.filter(
            company=customer.company,
            calling_station_id__iexact=mac,
            status=SessionStatus.ACTIVE,
        )

        count = 0
        for sess in active_sessions:
            try:
                disconnect_hotspot_session(
                    session=sess,
                    trigger_type=SessionDisconnectTrigger.MANUAL,
                    reason="Customer disconnected device via Self-Service Portal",
                )
                count += 1
            except Exception as exc:
                logger.warning("Failed self-service session disconnect for MAC %s: %s", mac, exc)

        return Response({
            "code": "device_disconnected",
            "detail": f"Disconnected {count} active session(s) for device {mac}.",
            "count": count,
        }, status=status.HTTP_200_OK)
