import redis
from django.conf import settings
from django.db import connection
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.companies.models import Company
from apps.core.models import IncidentStatus, ServiceIncident, SystemWatchdogConfig
from apps.core.services.watchdog_services import (
    run_full_watchdog_cycle,
    send_system_alert_sms,
)


class HealthCheckView(APIView):
    """
    Basic health check endpoint returning system status and database/redis connectivity.
    GET /api/v1/health/
    """
    permission_classes = [AllowAny]

    def get(self, request):
        db_status = "healthy"
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"

        redis_status = "healthy"
        try:
            r = redis.from_url(settings.REDIS_URL, socket_timeout=1)
            r.ping()
        except Exception as e:
            redis_status = f"unavailable (optional in dev): {str(e)}"

        overall_status = "healthy" if db_status == "healthy" else "degraded"

        return Response({
            "status": overall_status,
            "version": "1.0.0",
            "database": db_status,
            "redis": redis_status,
        })


class SystemWatchdogStatusView(APIView):
    """
    Real-time system health and watchdog probe matrix.
    GET /api/v1/health/watchdog/
    """
    permission_classes = [AllowAny]

    def get(self, request):
        company_id = request.query_params.get('company_id')
        company = None
        if company_id:
            company = Company.objects.filter(id=company_id).first()

        # Run probes on-demand (dry-run without sending alerts on GET request)
        cycle_result = run_full_watchdog_cycle(company=company, send_alerts=False)

        # Retrieve active and recent incidents
        active_incidents = ServiceIncident.objects.filter(
            resolved_at__isnull=True
        ).order_by('-detected_at')
        if company:
            active_incidents = active_incidents.filter(company=company)

        recent_resolved = ServiceIncident.objects.filter(
            resolved_at__isnull=False
        ).order_by('-resolved_at')[:5]
        if company:
            recent_resolved = recent_resolved.filter(company=company)

        # Retrieve config
        config = SystemWatchdogConfig.objects.filter(company=company, is_enabled=True).first()
        if not config:
            config = SystemWatchdogConfig.objects.filter(company__isnull=True, is_enabled=True).first()

        return Response({
            "timestamp": cycle_result['timestamp'],
            "overall_status": cycle_result['overall_status'],
            "probes": cycle_result['probes'],
            "active_incidents": [
                {
                    "id": str(inc.id),
                    "service_name": inc.service_name,
                    "service_identifier": inc.service_identifier,
                    "status": inc.status,
                    "error_message": inc.error_message,
                    "detected_at": inc.detected_at.isoformat(),
                    "alert_sent_at": inc.alert_sent_at.isoformat() if inc.alert_sent_at else None,
                    "alert_count": inc.alert_count,
                }
                for inc in active_incidents
            ],
            "recent_resolved": [
                {
                    "id": str(inc.id),
                    "service_name": inc.service_name,
                    "service_identifier": inc.service_identifier,
                    "status": inc.status,
                    "detected_at": inc.detected_at.isoformat(),
                    "resolved_at": inc.resolved_at.isoformat() if inc.resolved_at else None,
                    "alert_count": inc.alert_count,
                }
                for inc in recent_resolved
            ],
            "config": {
                "is_enabled": config.is_enabled if config else True,
                "alert_phone_numbers": config.alert_phone_numbers if config else "",
                "alert_cooldown_minutes": config.alert_cooldown_minutes if config else 30,
                "check_interval_seconds": config.check_interval_seconds if config else 60,
                "radius_host": config.radius_host if config else "127.0.0.1",
                "radius_auth_port": config.radius_auth_port if config else 1812,
                "notify_on_recovery": config.notify_on_recovery if config else True,
            } if config else None,
        })


class SystemWatchdogConfigView(APIView):
    """
    Retrieve or update System Watchdog settings and alert destination numbers.
    GET /api/v1/health/watchdog/config/
    PUT /api/v1/health/watchdog/config/
    """
    permission_classes = [AllowAny]

    def _get_config(self, company=None):
        config = SystemWatchdogConfig.objects.filter(company=company, is_enabled=True).first()
        if not config:
            config = SystemWatchdogConfig.objects.filter(company__isnull=True).first()
        if not config:
            config = SystemWatchdogConfig.objects.create(company=company, is_enabled=True)
        return config

    def get(self, request):
        config = self._get_config()
        return Response({
            "id": str(config.id),
            "is_enabled": config.is_enabled,
            "alert_phone_numbers": config.alert_phone_numbers,
            "alert_cooldown_minutes": config.alert_cooldown_minutes,
            "check_interval_seconds": config.check_interval_seconds,
            "radius_host": config.radius_host,
            "radius_auth_port": config.radius_auth_port,
            "radius_secret": config.radius_secret,
            "notify_on_recovery": config.notify_on_recovery,
        })

    def put(self, request):
        config = self._get_config()
        data = request.data

        if 'is_enabled' in data:
            config.is_enabled = bool(data['is_enabled'])
        if 'alert_phone_numbers' in data:
            config.alert_phone_numbers = str(data['alert_phone_numbers']).strip()
        if 'alert_cooldown_minutes' in data:
            config.alert_cooldown_minutes = max(1, int(data['alert_cooldown_minutes']))
        if 'check_interval_seconds' in data:
            config.check_interval_seconds = max(5, int(data['check_interval_seconds']))
        if 'radius_host' in data:
            config.radius_host = str(data['radius_host']).strip()
        if 'radius_auth_port' in data:
            config.radius_auth_port = int(data['radius_auth_port'])
        if 'radius_secret' in data:
            config.radius_secret = str(data['radius_secret'])
        if 'notify_on_recovery' in data:
            config.notify_on_recovery = bool(data['notify_on_recovery'])

        config.save()

        return Response({
            "status": "success",
            "message": "System Watchdog configuration updated.",
            "config": {
                "id": str(config.id),
                "is_enabled": config.is_enabled,
                "alert_phone_numbers": config.alert_phone_numbers,
                "alert_cooldown_minutes": config.alert_cooldown_minutes,
                "check_interval_seconds": config.check_interval_seconds,
                "radius_host": config.radius_host,
                "radius_auth_port": config.radius_auth_port,
                "notify_on_recovery": config.notify_on_recovery,
            }
        })


class SystemWatchdogTestSMSView(APIView):
    """
    Dispatches a verification test SMS to confirm operator alert phone number reception.
    POST /api/v1/health/watchdog/test-sms/
    Payload: {"phone_number": "+255712345678"} (optional; defaults to configured alert numbers)
    """
    permission_classes = [AllowAny]

    def post(self, request):
        phone_number = request.data.get('phone_number')
        config = SystemWatchdogConfig.objects.filter(is_enabled=True).first()

        target_phones = phone_number or (config.alert_phone_numbers if config else None)
        if not target_phones:
            return Response(
                {"error": "No recipient phone number provided and no default configured."},
                status=status.HTTP_400_BAD_REQUEST
            )

        messages = send_system_alert_sms(
            phone_numbers=target_phones,
            alert_title="TEST VERIFICATION ALERT",
            alert_message="This is a test notification from Usimamizi System Watchdog. SMS alerting is active and operational."
        )

        sent_count = sum(1 for m in messages if m.status == 'SENT')
        failed_count = sum(1 for m in messages if m.status == 'FAILED')

        return Response({
            "status": "dispatched",
            "recipients_contacted": len(messages),
            "delivered": sent_count,
            "failed": failed_count,
            "details": [
                {
                    "message_id": str(m.id),
                    "recipient": m.recipient,
                    "phone_normalized": m.phone_normalized,
                    "status": m.status,
                }
                for m in messages
            ]
        })
