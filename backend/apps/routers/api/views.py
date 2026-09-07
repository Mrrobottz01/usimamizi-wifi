import logging
from typing import Optional

from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.companies.models import Company
from apps.companies.permissions import IsCompanyMember
from apps.companies.selectors.company_selectors import get_company_by_id
from apps.routers.models import Router, RouterHealthStatus
from apps.routers.services.provisioning_service import (
    generate_router_bootstrap_script,
    provision_router_via_api,
)
from apps.routers.services.router_service import (
    collect_router_telemetry,
    set_router_credentials,
    test_router_connection,
)
from .serializers import (
    RouterCreateSerializer,
    RouterCredentialsSerializer,
    RouterSerializer,
)

logger = logging.getLogger(__name__)


def _get_request_company(request) -> Optional[Company]:
    company_id = None
    if request.method == 'GET':
        company_id = request.query_params.get('company_id')
    elif hasattr(request, 'data') and isinstance(request.data, dict):
        company_id = request.data.get('company_id') or request.query_params.get('company_id')

    if company_id:
        c = get_company_by_id(company_id)
        if c:
            return c

    # Fallback to user membership or first company
    c = Company.objects.filter(memberships__user=request.user, memberships__is_active=True).first()
    if not c:
        c = Company.objects.first()
    return c


class RouterListCreateView(APIView):
    """
    GET  /api/v1/routers/ — List routers for company with optional filters
    POST /api/v1/routers/ — Register a new router under company
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = _get_request_company(request)
        if not company:
            return Response({'detail': 'Company not found.'}, status=status.HTTP_404_NOT_FOUND)

        qs = Router.objects.filter(company=company).select_related('location').prefetch_related('hotspots')

        # Filter by location
        location_id = request.query_params.get('location')
        if location_id:
            qs = qs.filter(location_id=location_id)

        # Filter by health_status
        health_status = request.query_params.get('health_status')
        if health_status and health_status.upper() in RouterHealthStatus.values:
            qs = qs.filter(health_status=health_status.upper())

        # Filter by is_active
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')

        serializer = RouterSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        company = _get_request_company(request)
        if not company:
            return Response({'detail': 'Company not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = RouterCreateSerializer(data=request.data, context={'company': company})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            router = serializer.save()
            return Response(RouterSerializer(router).data, status=status.HTTP_201_CREATED)
        except ValidationError as exc:
            return Response({'detail': exc.message_dict if hasattr(exc, 'message_dict') else str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class RouterDetailView(APIView):
    """
    GET    /api/v1/routers/<id>/ — Retrieve router details
    PATCH  /api/v1/routers/<id>/ — Update router configuration
    DELETE /api/v1/routers/<id>/ — Remove or deactivate router
    """
    permission_classes = [IsAuthenticated]

    def _get_router(self, router_id, request) -> Optional[Router]:
        company = _get_request_company(request)
        if not company:
            return None
        return Router.objects.filter(id=router_id, company=company).select_related('location').first()

    def get(self, request, router_id):
        router = self._get_router(router_id, request)
        if not router:
            return Response({'detail': 'Router not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(RouterSerializer(router).data)

    def patch(self, request, router_id):
        router = self._get_router(router_id, request)
        if not router:
            return Response({'detail': 'Router not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = RouterSerializer(router, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            updated_router = serializer.save()
            return Response(RouterSerializer(updated_router).data)
        except ValidationError as exc:
            return Response({'detail': exc.message_dict if hasattr(exc, 'message_dict') else str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, router_id):
        router = self._get_router(router_id, request)
        if not router:
            return Response({'detail': 'Router not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Safety check: prevent deleting router if it has active hotspots
        active_hotspots = router.hotspots.filter(is_active=True).count()
        if active_hotspots > 0:
            return Response(
                {'detail': f'Cannot delete router hosting {active_hotspots} active hotspot(s). Deactivate or migrate them first.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        router.is_active = False
        router.save(update_fields=['is_active', 'updated_at'])
        return Response({'detail': f"Router '{router.name}' has been deactivated."}, status=status.HTTP_200_OK)


class RouterCredentialsView(APIView):
    """
    POST /api/v1/routers/<id>/credentials/ — Set or update encrypted RouterOS management credentials
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, router_id):
        company = _get_request_company(request)
        router = get_object_or_404(Router, id=router_id, company=company)

        serializer = RouterCredentialsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
            set_router_credentials(
                router=router,
                username=data['api_username'],
                password=data['api_password'],
                api_port=data.get('api_port'),
                use_tls=data.get('use_tls'),
            )
            return Response({
                'detail': 'Credentials successfully configured.',
                'has_credentials': router.has_credentials,
                'api_username': router.api_username,
                'api_port': router.api_port,
                'use_tls': router.use_tls,
            }, status=status.HTTP_200_OK)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class RouterTestConnectionView(APIView):
    """
    POST /api/v1/routers/<id>/test-connection/ — Run live connectivity test and return diagnostics
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, router_id):
        company = _get_request_company(request)
        router = get_object_or_404(Router, id=router_id, company=company)

        timeout = float(request.data.get('timeout', 4.0)) if hasattr(request, 'data') else 4.0
        diag = test_router_connection(router, timeout=timeout)
        return Response(diag, status=status.HTTP_200_OK if diag['success'] else status.HTTP_502_BAD_GATEWAY)


class RouterHealthView(APIView):
    """
    GET  /api/v1/routers/<id>/health/ — Read cached telemetry and health state from database
    POST /api/v1/routers/<id>/refresh-health/ — Poll live router telemetry and update database cache
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, router_id):
        company = _get_request_company(request)
        router = get_object_or_404(Router, id=router_id, company=company)

        return Response({
            'router_id': str(router.id),
            'router_name': router.name,
            'management_ip': router.management_ip,
            'health_status': router.health_status,
            'health_message': router.health_message,
            'last_seen_at': router.last_seen_at.isoformat() if router.last_seen_at else None,
            'last_health_check_at': router.last_health_check_at.isoformat() if router.last_health_check_at else None,
            'system_resources': router.system_resources,
            'has_credentials': router.has_credentials,
        })

    def post(self, request, router_id):
        company = _get_request_company(request)
        router = get_object_or_404(Router, id=router_id, company=company)

        timeout = float(request.data.get('timeout', 4.0)) if hasattr(request, 'data') else 4.0
        diag = collect_router_telemetry(router, timeout=timeout)
        router.refresh_from_db()

        return Response({
            'diag': diag,
            'router': RouterSerializer(router).data,
        }, status=status.HTTP_200_OK if diag['success'] else status.HTTP_502_BAD_GATEWAY)


class RouterProvisionView(APIView):
    """
    POST /api/v1/routers/<id>/provision/ — 1-Click Live API Provisioning
    Configures FreeRADIUS AAA, HotSpot server, Walled Garden, and Anti-Tethering policies over API port 8728.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, router_id):
        company = _get_request_company(request)
        router = get_object_or_404(Router, id=router_id, company=company)

        options = request.data if isinstance(request.data, dict) else {}
        result = provision_router_via_api(router, options=options)
        router.refresh_from_db()

        return Response({
            'result': result,
            'router': RouterSerializer(router).data,
        }, status=status.HTTP_200_OK if result['success'] else status.HTTP_502_BAD_GATEWAY)


class RouterBootstrapScriptView(APIView):
    """
    GET /api/v1/routers/<id>/bootstrap-script/ — Retrieve RouterOS bootstrap command and .rsc script
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, router_id):
        company = _get_request_company(request)
        router = get_object_or_404(Router, id=router_id, company=company)

        host = request.get_host()
        scheme = 'https' if request.is_secure() else 'http'
        base_url = f"{scheme}://{host}"
        raw_script_url = f"{base_url}/api/v1/routers/{router.id}/bootstrap.rsc"

        script_content = generate_router_bootstrap_script(
            router=router,
            radius_server_ip=request.query_params.get('radius_ip'),
            shared_secret=request.query_params.get('shared_secret'),
            portal_base_url=base_url,
            enable_anti_tethering=request.query_params.get('anti_tethering', 'true').lower() == 'true',
            enable_radius=request.query_params.get('radius', 'true').lower() == 'true',
            enable_hotspot=request.query_params.get('hotspot', 'true').lower() == 'true',
            enable_walled_garden=request.query_params.get('walled_garden', 'true').lower() == 'true',
        )

        command = f'/tool fetch url="{raw_script_url}" mode=http dst-path=usimamizi.rsc; /import usimamizi.rsc'

        return Response({
            'router_id': str(router.id),
            'router_name': router.name,
            'management_ip': str(router.management_ip),
            'command': command,
            'download_url': raw_script_url,
            'script': script_content,
        })


class RouterBootstrapRscRawView(APIView):
    """
    GET /api/v1/routers/<id>/bootstrap.rsc — Direct raw .rsc download for MikroTik /tool fetch
    """
    permission_classes = [AllowAny]

    def get(self, request, router_id):
        router = get_object_or_404(Router, id=router_id, is_active=True)

        host = request.get_host()
        scheme = 'https' if request.is_secure() else 'http'
        base_url = f"{scheme}://{host}"

        script_content = generate_router_bootstrap_script(
            router=router,
            portal_base_url=base_url,
        )

        response = HttpResponse(script_content, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = f'inline; filename="usimamizi_{router.id}.rsc"'
        return response

