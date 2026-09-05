import logging
from datetime import timedelta
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.companies.models import Company
from apps.companies.permissions import IsCompanyMember
from apps.companies.selectors.company_selectors import get_company_by_id
from apps.plans.models import Plan
from .serializers import (
    CustomerDeviceSerializer,
    CustomerSerializer,
    CustomerSubscriptionSettingsSerializer,
    SubscriptionEventSerializer,
    SubscriptionSerializer,
)
from ..models import (
    Customer,
    CustomerDevice,
    CustomerStatus,
    CustomerSubscriptionSettings,
    Subscription,
    SubscriptionEvent,
    SubscriptionRenewalMode,
    SubscriptionSource,
    SubscriptionStatus,
)
from ..services.customer_services import (
    block_customer,
    get_or_create_customer,
    normalize_customer_phone,
    reactivate_customer,
    register_or_update_device,
    suspend_customer,
)
from ..services.subscription_services import (
    create_subscription,
    reactivate_subscription,
    renew_subscription,
    suspend_subscription,
)

logger = logging.getLogger(__name__)


def _resolve_company(request) -> Company | None:
    company_id = request.query_params.get('company_id') or request.data.get('company_id')
    if company_id:
        return get_company_by_id(company_id)

    membership = getattr(request.user, 'memberships', None)
    if membership:
        m = membership.filter(is_active=True).first()
        if m:
            return m.company

    return getattr(request.user, 'company', None)


class CustomerListCreateView(APIView):
    """
    GET /api/v1/customers/?company_id={uuid}&q=...&status=...
    POST /api/v1/customers/ — Create or register a customer manually
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get(self, request):
        company = _resolve_company(request)
        if not company:
            return Response(
                {"code": "missing_company_id", "detail": "Target company not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.check_object_permissions(request, company)

        queryset = Customer.objects.filter(company=company).order_by('-last_seen_at', '-created_at')

        # Metrics calculation
        now = timezone.now()
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        total_customers = queryset.count()
        new_today = queryset.filter(created_at__gte=start_of_today).count()
        suspended_count = queryset.filter(status__in=[CustomerStatus.SUSPENDED, CustomerStatus.BLOCKED]).count()

        active_sub_cust_ids = Subscription.objects.filter(
            company=company,
            status__in=[SubscriptionStatus.ACTIVE, SubscriptionStatus.GRACE],
        ).values_list('customer_id', flat=True).distinct()

        active_subscribers = len(active_sub_cust_ids)
        expired_subscribers = max(0, total_customers - active_subscribers - suspended_count)

        # Filters
        query = request.query_params.get('q', '').strip()
        if query:
            queryset = queryset.filter(
                Q(normalized_phone__icontains=query) |
                Q(phone__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(email__icontains=query) |
                Q(devices__mac_address__icontains=query)
            ).distinct()

        status_filter = request.query_params.get('status', '').strip()
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        plan_filter = request.query_params.get('plan_id', '').strip()
        if plan_filter:
            queryset = queryset.filter(subscriptions__plan_id=plan_filter).distinct()

        serializer = CustomerSerializer(queryset[:200], many=True)
        return Response({
            "metrics": {
                "total_customers": total_customers,
                "active_subscribers": active_subscribers,
                "expired_subscribers": expired_subscribers,
                "suspended_count": suspended_count,
                "new_today": new_today,
            },
            "results": serializer.data,
        }, status=status.HTTP_200_OK)

    def post(self, request):
        company = _resolve_company(request)
        if not company:
            return Response({"code": "missing_company_id", "detail": "Company is required."}, status=status.HTTP_400_BAD_REQUEST)
        self.check_object_permissions(request, company)

        phone = request.data.get('phone', '').strip()
        if not phone:
            return Response({"code": "missing_phone", "detail": "Phone number is required."}, status=status.HTTP_400_BAD_REQUEST)

        first_name = request.data.get('first_name', '').strip()
        last_name = request.data.get('last_name', '').strip()
        email = request.data.get('email', '').strip()
        language = request.data.get('language', 'EN')
        notes = request.data.get('notes', '').strip()

        customer, created = get_or_create_customer(
            company=company,
            phone=phone,
            first_name=first_name,
            last_name=last_name,
            email=email,
            language=language,
            notes=notes,
        )

        return Response(CustomerSerializer(customer).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class CustomerDetailView(APIView):
    """
    GET /api/v1/customers/{id}/
    PATCH /api/v1/customers/{id}/
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def _get_customer(self, request, pk):
        try:
            customer = Customer.objects.get(pk=pk)
            self.check_object_permissions(request, customer.company)
            return customer
        except Customer.DoesNotExist:
            return None

    def get(self, request, pk):
        customer = self._get_customer(request, pk)
        if not customer:
            return Response({"code": "not_found", "detail": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(CustomerSerializer(customer).data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        customer = self._get_customer(request, pk)
        if not customer:
            return Response({"code": "not_found", "detail": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)

        for attr in ['first_name', 'last_name', 'email', 'language', 'notes']:
            if attr in request.data:
                setattr(customer, attr, request.data[attr])

        customer.save()
        return Response(CustomerSerializer(customer).data, status=status.HTTP_200_OK)


class CustomerSuspendView(APIView):
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def post(self, request, pk):
        try:
            customer = Customer.objects.get(pk=pk)
            self.check_object_permissions(request, customer.company)
        except Customer.DoesNotExist:
            return Response({"code": "not_found", "detail": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)

        reason = request.data.get('reason', 'Suspended by admin')
        customer = suspend_customer(customer=customer, reason=reason, user=request.user)
        return Response(CustomerSerializer(customer).data, status=status.HTTP_200_OK)


class CustomerReactivateView(APIView):
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def post(self, request, pk):
        try:
            customer = Customer.objects.get(pk=pk)
            self.check_object_permissions(request, customer.company)
        except Customer.DoesNotExist:
            return Response({"code": "not_found", "detail": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)

        customer = reactivate_customer(customer=customer, user=request.user)
        return Response(CustomerSerializer(customer).data, status=status.HTTP_200_OK)


class CustomerBlockView(APIView):
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def post(self, request, pk):
        try:
            customer = Customer.objects.get(pk=pk)
            self.check_object_permissions(request, customer.company)
        except Customer.DoesNotExist:
            return Response({"code": "not_found", "detail": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)

        reason = request.data.get('reason', 'Blocked by admin')
        customer = block_customer(customer=customer, reason=reason, user=request.user)
        return Response(CustomerSerializer(customer).data, status=status.HTTP_200_OK)


class CustomerDevicesView(APIView):
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get(self, request, pk):
        try:
            customer = Customer.objects.get(pk=pk)
            self.check_object_permissions(request, customer.company)
        except Customer.DoesNotExist:
            return Response({"code": "not_found", "detail": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)

        devices = customer.devices.all().order_by('-last_seen_at')
        return Response(CustomerDeviceSerializer(devices, many=True).data, status=status.HTTP_200_OK)

    def post(self, request, pk):
        try:
            customer = Customer.objects.get(pk=pk)
            self.check_object_permissions(request, customer.company)
        except Customer.DoesNotExist:
            return Response({"code": "not_found", "detail": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)

        mac = request.data.get('mac_address', '').strip()
        device_name = request.data.get('device_name', '').strip()
        device_type = request.data.get('device_type', 'OTHER')

        if not mac:
            return Response({"code": "missing_mac", "detail": "MAC address is required."}, status=status.HTTP_400_BAD_REQUEST)

        device = register_or_update_device(
            customer=customer,
            mac_address=mac,
            device_name=device_name,
            device_type=device_type,
        )
        return Response(CustomerDeviceSerializer(device).data, status=status.HTTP_201_CREATED)


class CustomerDeviceActionView(APIView):
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def post(self, request, pk, device_id, action):
        try:
            customer = Customer.objects.get(pk=pk)
            self.check_object_permissions(request, customer.company)
            device = customer.devices.get(pk=device_id)
        except (Customer.DoesNotExist, CustomerDevice.DoesNotExist):
            return Response({"code": "not_found", "detail": "Device not found."}, status=status.HTTP_404_NOT_FOUND)

        if action == 'toggle-trust':
            device.is_trusted = not device.is_trusted
            device.save(update_fields=['is_trusted'])
        elif action == 'toggle-block':
            device.is_blocked = not device.is_blocked
            device.save(update_fields=['is_blocked'])
        else:
            return Response({"code": "invalid_action", "detail": "Unknown action."}, status=status.HTTP_400_BAD_REQUEST)

        return Response(CustomerDeviceSerializer(device).data, status=status.HTTP_200_OK)


class CustomerSubscriptionsView(APIView):
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get(self, request, pk):
        try:
            customer = Customer.objects.get(pk=pk)
            self.check_object_permissions(request, customer.company)
        except Customer.DoesNotExist:
            return Response({"code": "not_found", "detail": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)

        subs = customer.subscriptions.all().select_related('plan', 'hotspot').order_by('-created_at')
        return Response(SubscriptionSerializer(subs, many=True).data, status=status.HTTP_200_OK)


class CustomerTimelineView(APIView):
    """
    Unified chronological event stream for a customer.
    Combines: Subscriptions, Payments, Sessions, SMS, Audit Logs.
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get(self, request, pk):
        try:
            customer = Customer.objects.get(pk=pk)
            self.check_object_permissions(request, customer.company)
        except Customer.DoesNotExist:
            return Response({"code": "not_found", "detail": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)

        events = []

        # 1. Subscription Events
        sub_events = SubscriptionEvent.objects.filter(
            subscription__customer=customer
        ).select_related('subscription__plan').order_by('-created_at')[:50]

        for se in sub_events:
            events.append({
                "type": "SUBSCRIPTION_EVENT",
                "title": f"Subscription {se.event_type.title()}",
                "description": f"Plan: {se.subscription.plan.name if se.subscription.plan else 'Unknown'} | {se.old_status} -> {se.new_status}",
                "timestamp": se.created_at.isoformat(),
                "metadata": se.metadata,
            })

        # 2. Payments
        from apps.payments.models import PaymentTransaction
        txns = PaymentTransaction.objects.filter(
            company_id=customer.company_id,
            customer_phone=customer.normalized_phone,
        ).order_by('-created_at')[:50]

        for tx in txns:
            events.append({
                "type": "PAYMENT",
                "title": f"Payment {tx.status.title()}",
                "description": f"{tx.currency} {tx.amount} ({tx.payment_method}) - Ref: {tx.provider_reference or tx.internal_reference}",
                "timestamp": (tx.completed_at or tx.created_at).isoformat(),
                "metadata": {"status": tx.status, "amount": str(tx.amount)},
            })

        # 3. Hotspot Sessions
        from apps.hotspot_sessions.models import HotspotSession
        sessions = HotspotSession.objects.filter(
            Q(consumer=customer) | Q(calling_station_id__in=customer.devices.values_list('mac_address', flat=True))
        ).order_by('-session_start_time')[:50]

        for sess in sessions:
            mb_used = round((sess.total_octets or 0) / (1024 * 1024), 2)
            events.append({
                "type": "HOTSPOT_SESSION",
                "title": f"Session {sess.status.title()}",
                "description": f"MAC: {sess.calling_station_id} | {sess.duration_seconds}s | {mb_used} MB",
                "timestamp": (sess.session_start_time or sess.created_at).isoformat(),
                "metadata": {"mac": sess.calling_station_id, "ip": sess.framed_ip_address},
            })

        # 4. Notification Messages (SMS)
        from apps.notifications.models import NotificationMessage
        sms_logs = NotificationMessage.objects.filter(
            company=customer.company,
            recipient=customer.normalized_phone,
        ).order_by('-created_at')[:50]

        for msg in sms_logs:
            events.append({
                "type": "SMS",
                "title": f"SMS {msg.status.title()}",
                "description": msg.rendered_content[:120] + ("..." if len(msg.rendered_content) > 120 else ""),
                "timestamp": msg.created_at.isoformat(),
                "metadata": {"provider": msg.provider_used, "recipient": msg.recipient},
            })

        # Sort combined timeline descending
        events.sort(key=lambda x: x["timestamp"], reverse=True)

        return Response(events[:100], status=status.HTTP_200_OK)


class SubscriptionListCreateView(APIView):
    """
    GET /api/v1/subscriptions/?company_id={uuid}&status=...&q=...
    POST /api/v1/subscriptions/ — Create manual subscription
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get(self, request):
        company = _resolve_company(request)
        if not company:
            return Response({"code": "missing_company_id", "detail": "Target company not found."}, status=status.HTTP_400_BAD_REQUEST)
        self.check_object_permissions(request, company)

        queryset = Subscription.objects.filter(company=company).select_related(
            'customer', 'plan', 'hotspot'
        ).order_by('-current_period_end', '-created_at')

        status_filter = request.query_params.get('status', '').strip()
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        query = request.query_params.get('q', '').strip()
        if query:
            queryset = queryset.filter(
                Q(customer__normalized_phone__icontains=query) |
                Q(customer__first_name__icontains=query) |
                Q(plan__name__icontains=query)
            )

        serializer = SubscriptionSerializer(queryset[:200], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        company = _resolve_company(request)
        if not company:
            return Response({"code": "missing_company_id", "detail": "Company is required."}, status=status.HTTP_400_BAD_REQUEST)
        self.check_object_permissions(request, company)

        customer_id = request.data.get('customer_id')
        plan_id = request.data.get('plan_id')
        hotspot_id = request.data.get('hotspot_id')

        try:
            customer = Customer.objects.get(pk=customer_id, company=company)
            plan = Plan.objects.get(pk=plan_id, company=company)
        except (Customer.DoesNotExist, Plan.DoesNotExist) as e:
            return Response({"code": "not_found", "detail": str(e)}, status=status.HTTP_404_NOT_FOUND)

        hotspot = None
        if hotspot_id:
            hotspot = company.hotspots.filter(pk=hotspot_id).first()

        subscription = create_subscription(
            customer=customer,
            plan=plan,
            hotspot=hotspot,
            source=SubscriptionSource.ADMIN_CREATED,
            user=request.user,
            auto_activate=True,
        )

        return Response(SubscriptionSerializer(subscription).data, status=status.HTTP_201_CREATED)


class SubscriptionDetailView(APIView):
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get(self, request, pk):
        try:
            subscription = Subscription.objects.select_related('customer', 'plan', 'hotspot').get(pk=pk)
            self.check_object_permissions(request, subscription.company)
        except Subscription.DoesNotExist:
            return Response({"code": "not_found", "detail": "Subscription not found."}, status=status.HTTP_404_NOT_FOUND)

        data = SubscriptionSerializer(subscription).data
        events = subscription.events.all()
        data['events'] = SubscriptionEventSerializer(events, many=True).data
        return Response(data, status=status.HTTP_200_OK)


class SubscriptionRenewView(APIView):
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def post(self, request, pk):
        try:
            subscription = Subscription.objects.get(pk=pk)
            self.check_object_permissions(request, subscription.company)
        except Subscription.DoesNotExist:
            return Response({"code": "not_found", "detail": "Subscription not found."}, status=status.HTTP_404_NOT_FOUND)

        sub, entitlement = renew_subscription(
            subscription=subscription,
            payment=None,
            user=request.user,
        )
        return Response(SubscriptionSerializer(sub).data, status=status.HTTP_200_OK)


class SubscriptionSuspendView(APIView):
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def post(self, request, pk):
        try:
            subscription = Subscription.objects.get(pk=pk)
            self.check_object_permissions(request, subscription.company)
        except Subscription.DoesNotExist:
            return Response({"code": "not_found", "detail": "Subscription not found."}, status=status.HTTP_404_NOT_FOUND)

        reason = request.data.get('reason', 'Suspended by admin')
        sub = suspend_subscription(subscription=subscription, reason=reason, user=request.user)
        return Response(SubscriptionSerializer(sub).data, status=status.HTTP_200_OK)


class SubscriptionReactivateView(APIView):
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def post(self, request, pk):
        try:
            subscription = Subscription.objects.get(pk=pk)
            self.check_object_permissions(request, subscription.company)
        except Subscription.DoesNotExist:
            return Response({"code": "not_found", "detail": "Subscription not found."}, status=status.HTTP_404_NOT_FOUND)

        sub, entitlement = reactivate_subscription(subscription=subscription, user=request.user)
        return Response(SubscriptionSerializer(sub).data, status=status.HTTP_200_OK)


class CustomerSubscriptionSettingsView(APIView):
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get(self, request):
        company = _resolve_company(request)
        if not company:
            return Response({"code": "missing_company_id", "detail": "Company required."}, status=status.HTTP_400_BAD_REQUEST)
        self.check_object_permissions(request, company)

        settings_obj, _ = CustomerSubscriptionSettings.objects.get_or_create(company=company)
        return Response(CustomerSubscriptionSettingsSerializer(settings_obj).data, status=status.HTTP_200_OK)

    def put(self, request):
        company = _resolve_company(request)
        if not company:
            return Response({"code": "missing_company_id", "detail": "Company required."}, status=status.HTTP_400_BAD_REQUEST)
        self.check_object_permissions(request, company)

        settings_obj, _ = CustomerSubscriptionSettings.objects.get_or_create(company=company)
        serializer = CustomerSubscriptionSettingsSerializer(settings_obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
