from django.core.exceptions import ValidationError
from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.companies.permissions import IsCompanyMember
from apps.companies.selectors.company_selectors import get_company_by_id
from apps.plans.selectors.plan_selectors import get_plan_by_id

from ..selectors.voucher_selectors import (
    get_batch_by_id,
    get_batches_for_company,
    get_vouchers_for_batch,
    search_vouchers,
)
from ..services.voucher_services import (
    export_batch_csv,
    export_batch_routeros_script,
    generate_voucher_batch,
    revoke_voucher,
)
from .serializers import (
    GenerateBatchSerializer,
    RevokeVoucherSerializer,
    VoucherBatchSerializer,
    VoucherSerializer,
)


class VoucherBatchListCreateView(APIView):
    """
    GET  /api/v1/voucher-batches/?company_id={uuid} — List batches
    POST /api/v1/voucher-batches/ — Generate new voucher batch
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
        batches = get_batches_for_company(company)
        return Response(VoucherBatchSerializer(batches, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        company_id = request.data.get('company_id') or request.query_params.get('company_id')
        if not company_id:
            return Response({"code": "missing_company_id", "detail": "'company_id' is required."}, status=status.HTTP_400_BAD_REQUEST)

        company = get_company_by_id(company_id)
        if not company:
            return Response({"code": "company_not_found", "detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, company)

        serializer = GenerateBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan = get_plan_by_id(serializer.validated_data['plan_id'], company=company)
        if not plan:
            return Response({"code": "plan_not_found", "detail": "Plan not found for this company."}, status=status.HTTP_404_NOT_FOUND)

        try:
            batch, vouchers = generate_voucher_batch(
                company=company,
                plan=plan,
                quantity=serializer.validated_data['quantity'],
                created_by=request.user,
                label=serializer.validated_data.get('label', ''),
                notes=serializer.validated_data.get('notes', ''),
                distribution_mode=serializer.validated_data.get('distribution_mode', 'UNSOLD'),
                expires_at=serializer.validated_data.get('expires_at')
            )
            return Response(VoucherBatchSerializer(batch).data, status=status.HTTP_201_CREATED)
        except ValidationError as err:
            return Response(
                {"code": "validation_error", "detail": "Batch generation failed.", "field_errors": err.message_dict if hasattr(err, 'message_dict') else {'detail': err.messages}},
                status=status.HTTP_400_BAD_REQUEST
            )


class VoucherBatchDetailView(APIView):
    """
    GET /api/v1/voucher-batches/{id}/ — Batch details & vouchers
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get(self, request, batch_id):
        batch = get_batch_by_id(batch_id)
        if not batch:
            return Response({"code": "batch_not_found", "detail": "Batch not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, batch.company)
        vouchers = get_vouchers_for_batch(batch)

        return Response({
            "batch": VoucherBatchSerializer(batch).data,
            "vouchers": VoucherSerializer(vouchers, many=True).data
        }, status=status.HTTP_200_OK)


class BatchPrintableCardsView(APIView):
    """
    GET /api/v1/voucher-batches/{id}/print/ — Printable card data for A4 sheet rendering
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get(self, request, batch_id):
        from ..services.voucher_services import get_printable_voucher_cards

        batch = get_batch_by_id(batch_id)
        if not batch:
            return Response({"code": "batch_not_found", "detail": "Batch not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, batch.company)
        cards = get_printable_voucher_cards(batch)
        return Response({
            "batch": VoucherBatchSerializer(batch).data,
            "cards": cards
        }, status=status.HTTP_200_OK)


class ExportRouterOSScriptView(APIView):
    """
    GET /api/v1/voucher-batches/{id}/export-routeros/ — Export RouterOS .rsc script
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get(self, request, batch_id):
        batch = get_batch_by_id(batch_id)
        if not batch:
            return Response({"code": "batch_not_found", "detail": "Batch not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, batch.company)
        profile_override = request.query_params.get('profile')
        rsc_content = export_batch_routeros_script(batch, profile_name=profile_override)

        response = HttpResponse(rsc_content, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="{batch.reference}.rsc"'
        return response


class ExportBatchCSVView(APIView):
    """
    GET /api/v1/voucher-batches/{id}/export-csv/ — Export CSV file
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get(self, request, batch_id):
        batch = get_batch_by_id(batch_id)
        if not batch:
            return Response({"code": "batch_not_found", "detail": "Batch not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, batch.company)
        csv_content = export_batch_csv(batch)

        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{batch.reference}.csv"'
        return response


class VoucherMetricsView(APIView):
    """
    GET /api/v1/vouchers/metrics/?company_id={uuid} — Aggregate voucher metrics
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get(self, request):
        from ..selectors.voucher_selectors import get_voucher_metrics

        company_id = request.query_params.get('company_id')
        if not company_id:
            return Response({"code": "missing_company_id", "detail": "'company_id' is required."}, status=status.HTTP_400_BAD_REQUEST)

        company = get_company_by_id(company_id)
        if not company:
            return Response({"code": "company_not_found", "detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, company)
        metrics = get_voucher_metrics(company)
        return Response(metrics, status=status.HTTP_200_OK)


class VoucherListView(APIView):
    """
    GET /api/v1/vouchers/?company_id={uuid}&q={search}&status={status}&batch_id={id} — List/Search vouchers
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

        query = request.query_params.get('q', '')
        v_status = request.query_params.get('status')
        batch_id = request.query_params.get('batch_id')
        plan_id = request.query_params.get('plan_id')
        dist_state = request.query_params.get('distribution_state')
        export_stat = request.query_params.get('export_status')

        vouchers = search_vouchers(
            company=company,
            query=query,
            status=v_status,
            batch_id=batch_id,
            plan_id=plan_id,
            distribution_state=dist_state,
            export_status=export_stat
        )

        return Response(VoucherSerializer(vouchers[:250], many=True).data, status=status.HTTP_200_OK)


class VoucherTimelineView(APIView):
    """
    GET /api/v1/vouchers/{id}/timeline/ — Chronological audit timeline
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get(self, request, voucher_id):
        from ..models import Voucher
        from ..selectors.voucher_selectors import get_voucher_timeline

        voucher = Voucher.objects.filter(id=voucher_id).first()
        if not voucher:
            return Response({"code": "voucher_not_found", "detail": "Voucher not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, voucher.company)
        timeline = get_voucher_timeline(voucher)
        return Response({
            "voucher": VoucherSerializer(voucher).data,
            "timeline": timeline
        }, status=status.HTTP_200_OK)


class SendVoucherSMSView(APIView):
    """
    POST /api/v1/vouchers/{id}/send-sms/ — Dispatch voucher via RafikiSMS
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def post(self, request, voucher_id):
        from apps.notifications.services.sms_services import send_voucher_sms
        from ..models import Voucher
        from .serializers import SendVoucherSMSSerializer

        voucher = Voucher.objects.filter(id=voucher_id).first()
        if not voucher:
            return Response({"code": "voucher_not_found", "detail": "Voucher not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, voucher.company)

        serializer = SendVoucherSMSSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        recipient_phone = serializer.validated_data['recipient_phone']

        try:
            notification = send_voucher_sms(
                voucher=voucher,
                recipient_phone=recipient_phone,
                company=voucher.company
            )
            return Response({
                "detail": f"SMS queued for delivery to {notification.phone_normalized or recipient_phone}.",
                "notification_id": str(notification.id),
                "status": notification.status,
                "voucher": VoucherSerializer(voucher).data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"code": "sms_dispatch_error", "detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReserveVoucherView(APIView):
    """
    POST /api/v1/vouchers/{id}/reserve/ — Reserve an available voucher
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def post(self, request, voucher_id):
        from ..models import Voucher
        from ..services.voucher_services import reserve_voucher
        from .serializers import ReserveVoucherSerializer

        voucher = Voucher.objects.filter(id=voucher_id).first()
        if not voucher:
            return Response({"code": "voucher_not_found", "detail": "Voucher not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, voucher.company)

        serializer = ReserveVoucherSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data.get('recipient_phone') or serializer.validated_data.get('customer_phone', '')
        dist_state = serializer.validated_data.get('distribution_state') or None

        try:
            reserved = reserve_voucher(
                voucher=voucher,
                company=voucher.company,
                customer_phone=phone,
                distribution_state=dist_state,
                reserved_by=request.user
            )
            return Response(VoucherSerializer(reserved).data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"code": "validation_error", "detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RevokeVoucherView(APIView):
    """
    POST /api/v1/vouchers/{id}/revoke/ — Revoke a voucher (cascades to entitlement & session POD disconnect)
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def post(self, request, voucher_id):
        from ..models import Voucher

        voucher = Voucher.objects.filter(id=voucher_id).first()
        if not voucher:
            return Response({"code": "voucher_not_found", "detail": "Voucher not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, voucher.company)

        serializer = RevokeVoucherSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        revoked = revoke_voucher(
            voucher=voucher,
            company=voucher.company,
            revoked_by=request.user,
            reason=serializer.validated_data.get('reason', '')
        )
        return Response(VoucherSerializer(revoked).data, status=status.HTTP_200_OK)

