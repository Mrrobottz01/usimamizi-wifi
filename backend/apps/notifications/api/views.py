import csv

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.companies.permissions import IsCompanyMember
from apps.companies.selectors.company_selectors import get_company_by_id

from ..models import (
    NotificationMessage,
    NotificationProviderConfiguration,
    NotificationStatus,
    SMSProviderSenderID,
)
from ..selectors.history_selectors import (
    calculate_sms_summary_metrics,
    get_sms_history_queryset,
)
from ..services.history_services import (
    retry_failed_notification,
)
from ..services.sms_services import (
    normalize_phone_number,
    route_and_send_sms,
    sync_provider_sender_ids,
)
from .serializers import (
    NotificationMessageSerializer,
    NotificationProviderConfigSerializer,
    SMSHistoryDetailSerializer,
    SMSHistoryListSerializer,
    SMSProviderSenderIDSerializer,
    TestSMSSerializer,
)


class NotificationSettingsView(APIView):
    """
    GET /api/v1/settings/notifications/?company_id={uuid} — Retrieve company SMS provider configs
    PATCH /api/v1/settings/notifications/ — Update provider config priority / active status
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

        configs = NotificationProviderConfiguration.objects.all().order_by('priority', 'created_at')

        return Response(NotificationProviderConfigSerializer(configs, many=True).data, status=status.HTTP_200_OK)

    def patch(self, request):
        company_id = request.data.get('company_id') or request.query_params.get('company_id')
        if not company_id:
            return Response({"code": "missing_company_id", "detail": "'company_id' is required."}, status=status.HTTP_400_BAD_REQUEST)

        company = get_company_by_id(company_id)
        if not company:
            return Response({"code": "company_not_found", "detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, company)

        config_id = request.data.get('id')
        config_code = request.data.get('code')

        config = None
        if config_id:
            config = NotificationProviderConfiguration.objects.filter(id=config_id).first()
        elif config_code:
            config = NotificationProviderConfiguration.objects.filter(code=config_code).first()

        if not config:
            return Response({"code": "config_not_found", "detail": "Provider configuration not found."}, status=status.HTTP_404_NOT_FOUND)

        if 'is_active' in request.data:
            config.is_active = bool(request.data['is_active'])
        if 'priority' in request.data:
            config.priority = int(request.data['priority'])
        if 'sender_id' in request.data:
            config.sender_id = str(request.data['sender_id']).strip()
        if 'default_sender_id' in request.data:
            config.default_sender_id = str(request.data['default_sender_id']).strip()

        config.save()

        return Response(NotificationProviderConfigSerializer(config).data, status=status.HTTP_200_OK)


class ProviderSenderIDsView(APIView):
    """
    GET /api/v1/settings/notifications/sms/providers/{id}/sender-ids/ — List sender IDs for provider
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

        config = NotificationProviderConfiguration.objects.filter(id=id).first()
        if not config:
            return Response({"code": "config_not_found", "detail": "Provider configuration not found."}, status=status.HTTP_404_NOT_FOUND)

        senders = SMSProviderSenderID.objects.filter(provider_configuration=config)
        return Response(SMSProviderSenderIDSerializer(senders, many=True).data, status=status.HTTP_200_OK)


class SyncProviderSenderIDsView(APIView):
    """
    POST /api/v1/settings/notifications/sms/providers/{id}/sync-sender-ids/ — Sync sender IDs from upstream provider
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

        config = NotificationProviderConfiguration.objects.filter(id=id).first()
        if not config:
            return Response({"code": "config_not_found", "detail": "Provider configuration not found."}, status=status.HTTP_404_NOT_FOUND)

        synced_senders = sync_provider_sender_ids(provider_config=config)

        return Response({
            "message": f"Successfully synchronized {len(synced_senders)} sender IDs.",
            "provider_code": config.code,
            "sender_ids": SMSProviderSenderIDSerializer(synced_senders, many=True).data,
            "default_sender_id": config.default_sender_id
        }, status=status.HTTP_200_OK)


class SetDefaultSenderIDView(APIView):
    """
    PATCH /api/v1/settings/notifications/sms/providers/{id}/default-sender/ — Set default sender ID
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def patch(self, request, id):
        company_id = request.data.get('company_id') or request.query_params.get('company_id')
        if not company_id:
            return Response({"code": "missing_company_id", "detail": "'company_id' is required."}, status=status.HTTP_400_BAD_REQUEST)

        company = get_company_by_id(company_id)
        if not company:
            return Response({"code": "company_not_found", "detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, company)

        config = NotificationProviderConfiguration.objects.filter(id=id).first()
        if not config:
            return Response({"code": "config_not_found", "detail": "Provider configuration not found."}, status=status.HTTP_404_NOT_FOUND)

        sender_id = request.data.get('sender_id')
        if not sender_id:
            return Response({"code": "missing_sender_id", "detail": "'sender_id' is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Mark all senders as is_default=False, then mark selected as True
        SMSProviderSenderID.objects.filter(provider_configuration=config).update(is_default=False)
        selected_obj = SMSProviderSenderID.objects.filter(provider_configuration=config, sender_id=sender_id).first()
        if selected_obj:
            selected_obj.is_default = True
            selected_obj.save()

        config.default_sender_id = sender_id
        config.sender_id = sender_id
        config.save()

        return Response(NotificationProviderConfigSerializer(config).data, status=status.HTTP_200_OK)


class SendTestSMSView(APIView):
    """
    POST /api/v1/settings/notifications/test-sms/ — Send a test SMS to verify provider integration
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

        serializer = TestSMSSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_norm = normalize_phone_number(serializer.validated_data['recipient_phone'])
        provider_code = serializer.validated_data.get('provider_code', '')
        sender_id = serializer.validated_data.get('sender_id', '')

        notification_msg = NotificationMessage.objects.create(
            company=company,
            channel='SMS',
            recipient=serializer.validated_data['recipient_phone'],
            phone_normalized=phone_norm,
            rendered_content=serializer.validated_data['message_text'],
            status=NotificationStatus.QUEUED
        )

        processed_msg = route_and_send_sms(
            notification_message=notification_msg,
            target_provider_code=provider_code,
            preferred_sender_id=sender_id
        )

        return Response(NotificationMessageSerializer(processed_msg).data, status=status.HTTP_200_OK)


class SMSWebhookView(APIView):
    """
    POST /api/v1/webhooks/sms/{provider}/ — Delivery report webhook endpoint
    Supports Beem, NextSMS, and RafikiSMS delivery status webhooks with idempotency protection.
    """
    permission_classes = [AllowAny]

    def post(self, request, provider):
        payload = request.data or {}
        data = payload.get('data', {}) if isinstance(payload.get('data'), dict) else payload

        ref_ids = [
            str(data.get('sms_log_id')) if data.get('sms_log_id') is not None else None,
            str(data.get('transaction_id')) if data.get('transaction_id') is not None else None,
            str(data.get('message_id')) if data.get('message_id') is not None else None,
            str(payload.get('request_id')) if payload.get('request_id') is not None else None,
            str(payload.get('messageId')) if payload.get('messageId') is not None else None,
        ]
        valid_refs = [r for r in ref_ids if r and r != 'None']

        status_raw = str(data.get('status') or payload.get('status') or '').strip().lower()

        if valid_refs:
            msg = NotificationMessage.objects.filter(attempts__provider_reference__in=valid_refs).first()
            if msg:
                if status_raw in ['delivered', 'success', '73']:
                    if msg.status != NotificationStatus.DELIVERED:
                        msg.status = NotificationStatus.DELIVERED
                        msg.delivered_at = msg.delivered_at or data.get('delivered_at') or payload.get('timestamp')
                        msg.save()
                elif status_raw in ['failed', 'undelivered', 'rejected']:
                    if msg.status != NotificationStatus.DELIVERED and msg.status != NotificationStatus.FAILED:
                        msg.status = NotificationStatus.FAILED
                        msg.failed_at = msg.failed_at or payload.get('timestamp')
                        msg.save()

        return Response({"status": "received", "provider": provider}, status=status.HTTP_200_OK)


# ==========================================
# SMS HISTORY & DELIVERY LOGS API ENDPOINTS
# ==========================================

class SMSHistoryListView(APIView):
    """
    GET /api/v1/notifications/sms/history/?company_id={uuid}
    Paginated list of SMS notifications with server-side filters, search, and metrics.
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

        # Build filters from query params
        filters = {
            'status': request.query_params.get('status'),
            'failed_only': request.query_params.get('failed_only') in ['true', '1'],
            'delivered_only': request.query_params.get('delivered_only') in ['true', '1'],
            'provider': request.query_params.get('provider'),
            'sender_id': request.query_params.get('sender_id'),
            'message_type': request.query_params.get('message_type') or request.query_params.get('template_code'),
            'date_from': request.query_params.get('date_from'),
            'date_to': request.query_params.get('date_to'),
            'phone': request.query_params.get('phone'),
            'voucher_code': request.query_params.get('voucher_code'),
            'voucher_batch': request.query_params.get('voucher_batch'),
            'search': request.query_params.get('search'),
            'sort_by': request.query_params.get('sort_by', '-created_at'),
        }

        qs = get_sms_history_queryset(company=company, filters=filters)

        # Pagination
        page_num = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('page_size', 20)), 100)

        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page_num)

        # Metrics for the overall tenant/company context
        summary = calculate_sms_summary_metrics(company=company, queryset=qs)

        serializer = SMSHistoryListSerializer(page_obj.object_list, many=True, context={'request': request})

        return Response({
            "results": serializer.data,
            "count": paginator.count,
            "page": page_num,
            "page_size": page_size,
            "total_pages": paginator.num_pages,
            "summary": summary
        }, status=status.HTTP_200_OK)


class SMSHistoryDetailView(APIView):
    """
    GET /api/v1/notifications/sms/history/{id}/?company_id={uuid}
    Detailed view of an SMS notification including all failover delivery attempts and voucher metadata.
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

        msg = NotificationMessage.objects.filter(
            id=id,
            company=company
        ).select_related(
            'template',
            'voucher',
            'voucher__plan',
            'voucher__batch'
        ).prefetch_related(
            'attempts'
        ).first()

        if not msg:
            return Response({"code": "not_found", "detail": "SMS notification not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(SMSHistoryDetailSerializer(msg).data, status=status.HTTP_200_OK)


class SMSRetryView(APIView):
    """
    POST /api/v1/notifications/sms/history/{id}/retry/
    Safely re-enter SMS routing for a FAILED message.
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

        try:
            retried_msg = retry_failed_notification(message_id=id, company=company)
            return Response(SMSHistoryDetailSerializer(retried_msg).data, status=status.HTTP_200_OK)
        except ValidationError as err:
            return Response({"code": "invalid_retry", "detail": err.message_dict if hasattr(err, 'message_dict') else str(err)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as err:
            return Response({"code": "retry_error", "detail": str(err)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SMSHistoryExportView(APIView):
    """
    GET /api/v1/notifications/sms/history/export/?company_id={uuid}
    Export filtered SMS history as a CSV file.
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
            'failed_only': request.query_params.get('failed_only') in ['true', '1'],
            'delivered_only': request.query_params.get('delivered_only') in ['true', '1'],
            'provider': request.query_params.get('provider'),
            'sender_id': request.query_params.get('sender_id'),
            'message_type': request.query_params.get('message_type') or request.query_params.get('template_code'),
            'date_from': request.query_params.get('date_from'),
            'date_to': request.query_params.get('date_to'),
            'search': request.query_params.get('search'),
        }

        qs = get_sms_history_queryset(company=company, filters=filters)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="sms_history_{company.id}_{company.name.lower().replace(" ", "_")}.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'ID',
            'Date Created',
            'Recipient (Masked)',
            'Recipient (Full)',
            'Message Type',
            'Status',
            'Provider Used',
            'Sender ID',
            'Attempt Count',
            'Provider Reference',
            'Voucher Code',
            'Plan Name',
            'Delivered At',
        ])

        for item in qs[:1000]:
            serializer = SMSHistoryListSerializer(item)
            data = serializer.data
            writer.writerow([
                data['id'],
                data['created_at'],
                data['recipient_masked'],
                data['phone_normalized'] or data['recipient'],
                data['message_type'],
                data['status'],
                data['provider_used'],
                data['sender_id'],
                data['attempt_count'],
                data['provider_reference'],
                data['voucher_code'] or '',
                data['plan_name'] or '',
                data['delivered_at'] or '',
            ])

        return response
