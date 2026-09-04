from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.companies.permissions import IsCompanyMember
from apps.companies.selectors.company_selectors import get_company_by_id
from apps.plans.selectors.plan_selectors import get_plan_by_id

from ..exceptions import InvalidEntitlementStateTransition
from ..models import AccessEntitlement
from ..selectors.entitlement_selectors import (
    calculate_entitlement_summary_metrics,
    get_entitlements_queryset,
)
from ..services.entitlement_services import (
    activate_entitlement,
    grant_manual_entitlement,
    resume_entitlement,
    revoke_entitlement,
    suspend_entitlement,
)
from .serializers import (
    AccessEntitlementDetailSerializer,
    AccessEntitlementListSerializer,
    ManualGrantSerializer,
    RevokeEntitlementSerializer,
    SuspendEntitlementSerializer,
)


class EntitlementListView(APIView):
    """
    GET /api/v1/entitlements/?company_id={uuid}
    List, filter, and search Access Entitlements with summary metrics and pagination.
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

        filters = {
            'status': request.query_params.get('status'),
            'source_type': request.query_params.get('source_type'),
            'plan_id': request.query_params.get('plan') or request.query_params.get('plan_id'),
            'voucher_id': request.query_params.get('voucher') or request.query_params.get('voucher_id'),
            'voucher_code': request.query_params.get('voucher_code'),
            'date_from': request.query_params.get('date_from'),
            'date_to': request.query_params.get('date_to'),
            'expires_before': request.query_params.get('expires_before'),
            'expires_after': request.query_params.get('expires_after'),
            'search': request.query_params.get('search'),
            'sort_by': request.query_params.get('sort_by', '-created_at'),
        }

        qs = get_entitlements_queryset(company=company, filters=filters)

        page_num = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('page_size', 20)), 100)

        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page_num)

        summary = calculate_entitlement_summary_metrics(company=company, queryset=qs)
        serializer = AccessEntitlementListSerializer(page_obj.object_list, many=True)

        return Response({
            "results": serializer.data,
            "count": paginator.count,
            "page": page_num,
            "page_size": page_size,
            "total_pages": paginator.num_pages,
            "summary": summary
        }, status=status.HTTP_200_OK)


class EntitlementDetailView(APIView):
    """
    GET /api/v1/entitlements/{id}/?company_id={uuid}
    Retrieve full details of an Access Entitlement including immutable snapshot and live authorization status.
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get(self, request, id):
        company_id = request.query_params.get('company_id')
        if not company_id:
            return Response({"code": "missing_company_id", "detail": "'company_id' is required."}, status=status.HTTP_400_BAD_REQUEST)

        company = get_company_by_id(company_id)
        if not company:
            return Response({"code": "company_not_found", "detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, company)

        entitlement = AccessEntitlement.objects.filter(
            id=id,
            company=company
        ).select_related(
            'plan',
            'voucher',
            'voucher__batch',
            'customer',
            'created_by',
            'suspended_by',
            'revoked_by'
        ).first()

        if not entitlement:
            return Response({"code": "not_found", "detail": "Access entitlement not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(AccessEntitlementDetailSerializer(entitlement).data, status=status.HTTP_200_OK)


class ManualGrantView(APIView):
    """
    POST /api/v1/entitlements/manual-grant/
    Grant complimentary or administrative access manually.
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def post(self, request):
        company_id = request.data.get('company_id') or request.query_params.get('company_id')
        if not company_id:
            return Response({"code": "missing_company_id", "detail": "'company_id' is required."}, status=status.HTTP_400_BAD_REQUEST)

        company = get_company_by_id(company_id)
        if not company:
            return Response({"code": "company_not_found", "detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, company)

        serializer = ManualGrantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan = get_plan_by_id(serializer.validated_data['plan_id'])
        if not plan:
            return Response({"code": "plan_not_found", "detail": "Plan not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            entitlement = grant_manual_entitlement(
                company=company,
                plan=plan,
                actor=request.user,
                reason=serializer.validated_data['reason']
            )
            return Response(AccessEntitlementDetailSerializer(entitlement).data, status=status.HTTP_201_CREATED)
        except ValidationError as err:
            return Response({"code": "validation_error", "detail": err.message_dict if hasattr(err, 'message_dict') else str(err)}, status=status.HTTP_400_BAD_REQUEST)


class ActivateEntitlementView(APIView):
    """
    POST /api/v1/entitlements/{id}/activate/
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def post(self, request, id):
        company_id = request.data.get('company_id') or request.query_params.get('company_id')
        if not company_id:
            return Response({"code": "missing_company_id", "detail": "'company_id' is required."}, status=status.HTTP_400_BAD_REQUEST)

        company = get_company_by_id(company_id)
        if not company:
            return Response({"code": "company_not_found", "detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, company)

        entitlement = AccessEntitlement.objects.filter(id=id, company=company).first()
        if not entitlement:
            return Response({"code": "not_found", "detail": "Access entitlement not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            activated = activate_entitlement(entitlement=entitlement)
            return Response(AccessEntitlementDetailSerializer(activated).data, status=status.HTTP_200_OK)
        except InvalidEntitlementStateTransition as err:
            return Response({"code": "invalid_transition", "detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class SuspendEntitlementView(APIView):
    """
    POST /api/v1/entitlements/{id}/suspend/
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def post(self, request, id):
        company_id = request.data.get('company_id') or request.query_params.get('company_id')
        if not company_id:
            return Response({"code": "missing_company_id", "detail": "'company_id' is required."}, status=status.HTTP_400_BAD_REQUEST)

        company = get_company_by_id(company_id)
        if not company:
            return Response({"code": "company_not_found", "detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, company)

        entitlement = AccessEntitlement.objects.filter(id=id, company=company).first()
        if not entitlement:
            return Response({"code": "not_found", "detail": "Access entitlement not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = SuspendEntitlementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            suspended = suspend_entitlement(
                entitlement=entitlement,
                actor=request.user,
                reason=serializer.validated_data.get('reason', '')
            )
            return Response(AccessEntitlementDetailSerializer(suspended).data, status=status.HTTP_200_OK)
        except InvalidEntitlementStateTransition as err:
            return Response({"code": "invalid_transition", "detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class ResumeEntitlementView(APIView):
    """
    POST /api/v1/entitlements/{id}/resume/
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def post(self, request, id):
        company_id = request.data.get('company_id') or request.query_params.get('company_id')
        if not company_id:
            return Response({"code": "missing_company_id", "detail": "'company_id' is required."}, status=status.HTTP_400_BAD_REQUEST)

        company = get_company_by_id(company_id)
        if not company:
            return Response({"code": "company_not_found", "detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, company)

        entitlement = AccessEntitlement.objects.filter(id=id, company=company).first()
        if not entitlement:
            return Response({"code": "not_found", "detail": "Access entitlement not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            resumed = resume_entitlement(entitlement=entitlement, actor=request.user)
            return Response(AccessEntitlementDetailSerializer(resumed).data, status=status.HTTP_200_OK)
        except InvalidEntitlementStateTransition as err:
            return Response({"code": "invalid_transition", "detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class RevokeEntitlementView(APIView):
    """
    POST /api/v1/entitlements/{id}/revoke/
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def post(self, request, id):
        company_id = request.data.get('company_id') or request.query_params.get('company_id')
        if not company_id:
            return Response({"code": "missing_company_id", "detail": "'company_id' is required."}, status=status.HTTP_400_BAD_REQUEST)

        company = get_company_by_id(company_id)
        if not company:
            return Response({"code": "company_not_found", "detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, company)

        entitlement = AccessEntitlement.objects.filter(id=id, company=company).first()
        if not entitlement:
            return Response({"code": "not_found", "detail": "Access entitlement not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = RevokeEntitlementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            revoked = revoke_entitlement(
                entitlement=entitlement,
                actor=request.user,
                reason=serializer.validated_data['reason']
            )
            return Response(AccessEntitlementDetailSerializer(revoked).data, status=status.HTTP_200_OK)
        except InvalidEntitlementStateTransition as err:
            return Response({"code": "invalid_transition", "detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as err:
            return Response({"code": "validation_error", "detail": err.message_dict if hasattr(err, 'message_dict') else str(err)}, status=status.HTTP_400_BAD_REQUEST)


class EntitlementReleaseDeviceView(APIView):
    """
    POST /api/v1/entitlements/{id}/release-device/
    Release a bound MAC address to allow device replacement.
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def post(self, request, id):
        company_id = request.data.get('company_id') or request.query_params.get('company_id')
        if not company_id:
            return Response({"code": "missing_company_id", "detail": "'company_id' is required."}, status=status.HTTP_400_BAD_REQUEST)

        company = get_company_by_id(company_id)
        if not company:
            return Response({"code": "company_not_found", "detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, company)

        entitlement = AccessEntitlement.objects.filter(id=id, company=company).first()
        if not entitlement:
            return Response({"code": "not_found", "detail": "Access entitlement not found."}, status=status.HTTP_404_NOT_FOUND)

        mac_address = request.data.get('mac_address')
        if not mac_address:
            return Response({"code": "missing_mac", "detail": "'mac_address' is required."}, status=status.HTTP_400_BAD_REQUEST)

        reason = request.data.get('reason', 'Device replaced by operator')

        from apps.hotspot_sessions.services.session_control import release_entitlement_device
        try:
            released = release_entitlement_device(
                entitlement=entitlement,
                mac_address=mac_address,
                company=company,
                user=request.user,
                reason=reason
            )
            if not released:
                return Response({"code": "device_not_found", "detail": "Device MAC not currently bound to this entitlement."}, status=status.HTTP_404_NOT_FOUND)
            return Response({"success": True, "detail": f"Device {mac_address} released successfully."}, status=status.HTTP_200_OK)
        except ValidationError as err:
            return Response({"code": "validation_error", "detail": err.message_dict if hasattr(err, 'message_dict') else str(err)}, status=status.HTTP_400_BAD_REQUEST)
