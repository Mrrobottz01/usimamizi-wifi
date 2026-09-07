from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

import logging

from apps.companies.services.portal_services import get_plans_for_hotspot, resolve_hotspot_by_slug
from apps.payments.api.serializers import (
    InitiatePurchaseSerializer,
    PublicPlanSerializer,
    PublicPurchaseStatusSerializer,
)
from apps.payments.models import AccessPurchase, PaymentStatus, PurchaseStatus
from apps.payments.services.purchase_services import (
    get_payment_adapter,
    get_payment_config,
    initiate_access_purchase,
    process_payment_failure,
    process_verified_payment_completed,
)
from apps.plans.models import Plan

logger = logging.getLogger(__name__)


class PublicHotspotPlansView(APIView):
    """
    GET /api/v1/public/hotspots/{slug}/plans/
    List active internet access packages available for self-service purchase on this HotSpot.
    """
    permission_classes = [AllowAny]

    def get(self, request, slug):
        hotspot = resolve_hotspot_by_slug(slug)
        if not hotspot:
            return Response({
                "code": "HOTSPOT_NOT_FOUND",
                "detail": "Wi-Fi HotSpot configuration not found."
            }, status=status.HTTP_404_NOT_FOUND)

        plans = get_plans_for_hotspot(hotspot, include_inactive=False).order_by('price')
        serializer = PublicPlanSerializer(plans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PublicInitiatePurchaseView(APIView):
    """
    POST /api/v1/public/hotspots/{slug}/purchases/
    Customer initiates self-service mobile money purchase on the captive portal.
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
                "detail": "This HotSpot is currently inactive."
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = InitiatePurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        available_plans = get_plans_for_hotspot(hotspot, include_inactive=False)
        plan = available_plans.filter(id=data['plan_id']).first()
        if not plan:
            return Response({
                "code": "PLAN_NOT_FOUND",
                "detail": "The selected plan is not available on this HotSpot or is no longer active."
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            purchase, txn, result = initiate_access_purchase(
                company=hotspot.company,
                hotspot=hotspot,
                plan=plan,
                customer_phone=data['customer_phone'],
                client_mac=data.get('client_mac', ''),
                ip_address=data.get('ip_address'),
                metadata={"user_agent": request.META.get('HTTP_USER_AGENT', '')}
            )
        except ValueError as e:
            return Response({
                "code": "INVALID_PHONE",
                "detail": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "code": "PURCHASE_FAILED",
                "detail": f"Failed to initiate payment: {e}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "purchase_reference": purchase.reference,
            "status": purchase.status,
            "amount": float(purchase.amount),
            "currency": purchase.currency,
            "customer_phone": purchase.customer_phone,
            "checkout_url": result.get('checkout_url', ''),
            "payment_link_url": result.get('payment_link_url', ''),
            "message": f"Payment request sent to {purchase.customer_phone}. Please check your phone and enter your Mobile Money PIN."
        }, status=status.HTTP_201_CREATED)


class PublicPurchaseStatusView(APIView):
    """
    GET /api/v1/public/purchases/{reference}/status/
    Poll status of an in-flight purchase from the captive portal.
    """
    permission_classes = [AllowAny]

    def get(self, request, reference):
        purchase = AccessPurchase.objects.select_related('plan', 'voucher', 'entitlement', 'company').filter(
            reference=reference
        ).first()

        if not purchase:
            return Response({
                "code": "NOT_FOUND",
                "detail": "Purchase reference not found."
            }, status=status.HTTP_404_NOT_FOUND)

        # Real-time reconciliation: If still pending, query Snippe API directly
        if purchase.status == PurchaseStatus.PAYMENT_PENDING:
            txn = purchase.transactions.first()
            if txn and txn.provider_reference:
                try:
                    config = get_payment_config(purchase.company)
                    adapter = get_payment_adapter(config)
                    remote_status = adapter.get_payment_status(txn.provider_reference)

                    if remote_status.status == PaymentStatus.COMPLETED:
                        process_verified_payment_completed(
                            provider_reference=txn.provider_reference,
                            internal_reference=txn.internal_reference,
                            amount_paid=remote_status.amount,
                            currency=remote_status.currency or purchase.currency,
                            raw_payload=remote_status.raw_response
                        )
                        purchase.refresh_from_db()
                    elif remote_status.status in [PaymentStatus.FAILED, PaymentStatus.EXPIRED, PaymentStatus.CANCELLED]:
                        process_payment_failure(
                            provider_reference=txn.provider_reference,
                            internal_reference=txn.internal_reference,
                            failure_reason=remote_status.error_message,
                            raw_payload=remote_status.raw_response
                        )
                        purchase.refresh_from_db()
                except Exception as poll_err:
                    logger.warning("Error checking remote payment status for purchase %s: %s", purchase.reference, poll_err)

        serializer = PublicPurchaseStatusSerializer(purchase)
        return Response(serializer.data, status=status.HTTP_200_OK)
