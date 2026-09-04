from decimal import Decimal

from django.core.paginator import Paginator
from django.db import models
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.companies.permissions import IsCompanyMember
from apps.companies.selectors.company_selectors import get_company_by_id
from apps.payments.api.serializers import (
    AccessPurchaseSerializer,
    ApplyPresetSerializer,
    PaymentSettingsSerializer,
    PaymentTransactionSerializer,
    WalledGardenEntrySerializer,
)
from apps.payments.models import (
    AccessPurchase,
    HotspotWalledGardenEntry,
    PaymentStatus,
    PaymentTransaction,
    PurchaseStatus,
)
from apps.payments.services.purchase_services import get_payment_config
from apps.payments.services.walled_garden_services import (
    apply_walled_garden_preset,
    generate_routeros_walled_garden_script,
)


class BaseTenantPaymentView(APIView):
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get_tenant_company(self, request):
        company_id = request.query_params.get('company_id') or request.data.get('company_id')
        if not company_id:
            return None, Response(
                {"code": "missing_company_id", "detail": "'company_id' is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        company = get_company_by_id(company_id)
        if not company:
            return None, Response(
                {"code": "company_not_found", "detail": "Company not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        self.check_object_permissions(request, company)
        return company, None


class PaymentTransactionListView(BaseTenantPaymentView):
    """
    GET /api/v1/payments/?company_id={uuid}&status={status}&search={search}&page={page}
    """
    def get(self, request):
        company, err_resp = self.get_tenant_company(request)
        if err_resp:
            return err_resp

        qs = PaymentTransaction.objects.filter(company=company).select_related('purchase', 'purchase__plan')

        status_param = request.query_params.get('status')
        if status_param and status_param in PaymentStatus.values:
            qs = qs.filter(status=status_param)

        search = request.query_params.get('search')
        if search:
            search = search.strip()
            qs = qs.filter(
                models.Q(internal_reference__icontains=search) |
                models.Q(provider_reference__icontains=search) |
                models.Q(customer_phone__icontains=search) |
                models.Q(purchase__reference__icontains=search)
            )

        page_num = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('page_size', 20)), 100)

        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page_num)

        serializer = PaymentTransactionSerializer(page_obj.object_list, many=True)
        return Response({
            "results": serializer.data,
            "count": paginator.count,
            "page": page_num,
            "page_size": page_size,
            "total_pages": paginator.num_pages,
        }, status=status.HTTP_200_OK)


class PaymentTransactionDetailView(BaseTenantPaymentView):
    """
    GET /api/v1/payments/{id}/?company_id={uuid}
    """
    def get(self, request, id):
        company, err_resp = self.get_tenant_company(request)
        if err_resp:
            return err_resp

        txn = PaymentTransaction.objects.filter(id=id, company=company).select_related(
            'purchase', 'purchase__plan'
        ).first()

        if not txn:
            return Response({"code": "not_found", "detail": "Transaction not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(PaymentTransactionSerializer(txn).data, status=status.HTTP_200_OK)


class AccessPurchaseListView(BaseTenantPaymentView):
    """
    GET /api/v1/purchases/?company_id={uuid}&status={status}&page={page}
    """
    def get(self, request):
        company, err_resp = self.get_tenant_company(request)
        if err_resp:
            return err_resp

        qs = AccessPurchase.objects.filter(company=company).select_related(
            'plan', 'hotspot', 'voucher', 'entitlement'
        )

        status_param = request.query_params.get('status')
        if status_param and status_param in PurchaseStatus.values:
            qs = qs.filter(status=status_param)

        search = request.query_params.get('search')
        if search:
            search = search.strip()
            qs = qs.filter(
                models.Q(reference__icontains=search) |
                models.Q(customer_phone__icontains=search) |
                models.Q(voucher__display_code__icontains=search)
            )

        page_num = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('page_size', 20)), 100)

        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page_num)

        serializer = AccessPurchaseSerializer(page_obj.object_list, many=True)
        return Response({
            "results": serializer.data,
            "count": paginator.count,
            "page": page_num,
            "page_size": page_size,
            "total_pages": paginator.num_pages,
        }, status=status.HTTP_200_OK)


class AccessPurchaseDetailView(BaseTenantPaymentView):
    """
    GET /api/v1/purchases/{id}/?company_id={uuid}
    """
    def get(self, request, id):
        company, err_resp = self.get_tenant_company(request)
        if err_resp:
            return err_resp

        purchase = AccessPurchase.objects.filter(id=id, company=company).select_related(
            'plan', 'hotspot', 'voucher', 'entitlement'
        ).first()

        if not purchase:
            return Response({"code": "not_found", "detail": "Purchase not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(AccessPurchaseSerializer(purchase).data, status=status.HTTP_200_OK)


class PaymentSummaryMetricsView(BaseTenantPaymentView):
    """
    GET /api/v1/payments/reports/summary/?company_id={uuid}
    Accurate financial summary for tenant dashboard.
    """
    def get(self, request):
        company, err_resp = self.get_tenant_company(request)
        if err_resp:
            return err_resp

        now = timezone.now()
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        txns = PaymentTransaction.objects.filter(company=company)

        today_completed = txns.filter(status=PaymentStatus.COMPLETED, completed_at__gte=start_of_today)
        today_revenue = today_completed.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

        total_completed = txns.filter(status=PaymentStatus.COMPLETED)
        total_revenue = total_completed.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

        pending_count = txns.filter(status=PaymentStatus.PENDING).count()
        failed_count = txns.filter(status=PaymentStatus.FAILED).count()
        completed_count = total_completed.count()

        # Revenue by Plan breakdown
        plan_breakdown = (
            AccessPurchase.objects.filter(company=company, status=PurchaseStatus.FULFILLED)
            .values('plan__name')
            .annotate(revenue=models.Sum('amount'), count=models.Count('id'))
            .order_by('-revenue')[:5]
        )

        return Response({
            "today_revenue": float(today_revenue),
            "total_revenue": float(total_revenue),
            "completed_count": completed_count,
            "pending_count": pending_count,
            "failed_count": failed_count,
            "top_plans": list(plan_breakdown)
        }, status=status.HTTP_200_OK)


class PaymentSettingsView(BaseTenantPaymentView):
    """
    GET / PUT /api/v1/payments/settings/?company_id={uuid}
    """
    def get(self, request):
        company, err_resp = self.get_tenant_company(request)
        if err_resp:
            return err_resp

        config = get_payment_config(company)
        serializer = PaymentSettingsSerializer(config)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        company, err_resp = self.get_tenant_company(request)
        if err_resp:
            return err_resp

        config = get_payment_config(company)
        serializer = PaymentSettingsSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class HotspotWalledGardenListView(BaseTenantPaymentView):
    """
    GET / POST /api/v1/hotspots/walled-garden/?company_id={uuid}
    """
    def get(self, request):
        company, err_resp = self.get_tenant_company(request)
        if err_resp:
            return err_resp

        entries = HotspotWalledGardenEntry.objects.filter(company=company)
        serializer = WalledGardenEntrySerializer(entries, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        company, err_resp = self.get_tenant_company(request)
        if err_resp:
            return err_resp

        serializer = WalledGardenEntrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry = serializer.save(company=company)
        return Response(WalledGardenEntrySerializer(entry).data, status=status.HTTP_201_CREATED)


class HotspotWalledGardenDetailView(BaseTenantPaymentView):
    """
    DELETE /api/v1/hotspots/walled-garden/{id}/?company_id={uuid}
    """
    def delete(self, request, id):
        company, err_resp = self.get_tenant_company(request)
        if err_resp:
            return err_resp

        entry = HotspotWalledGardenEntry.objects.filter(id=id, company=company).first()
        if not entry:
            return Response({"code": "not_found", "detail": "Walled garden entry not found."}, status=status.HTTP_404_NOT_FOUND)

        entry.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ApplyWalledGardenPresetView(BaseTenantPaymentView):
    """
    POST /api/v1/hotspots/walled-garden/presets/apply/?company_id={uuid}
    """
    def post(self, request):
        company, err_resp = self.get_tenant_company(request)
        if err_resp:
            return err_resp

        serializer = ApplyPresetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        preset_name = serializer.validated_data['preset_name']
        hotspot_id = serializer.validated_data.get('hotspot_id')
        hotspot = company.hotspots.filter(id=hotspot_id).first() if hotspot_id else None

        created = apply_walled_garden_preset(company=company, hotspot=hotspot, preset_name=preset_name)
        return Response({
            "message": f"Successfully applied preset '{preset_name}'.",
            "entries_count": len(created)
        }, status=status.HTTP_200_OK)


class ExportRouterOSWalledGardenView(BaseTenantPaymentView):
    """
    GET /api/v1/hotspots/walled-garden/export-routeros/?company_id={uuid}
    """
    def get(self, request):
        company, err_resp = self.get_tenant_company(request)
        if err_resp:
            return err_resp

        script = generate_routeros_walled_garden_script(company=company)
        return Response({
            "script": script,
            "filename": f"walled-garden-{company.name.lower().replace(' ', '-')}.rsc"
        }, status=status.HTTP_200_OK)
