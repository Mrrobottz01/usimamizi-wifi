import redis
from django.conf import settings
from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """
    Health check endpoint returning system status and component health.
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
