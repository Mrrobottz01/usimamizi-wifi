import logging
from typing import Optional
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditLog
from apps.companies.models import Company
from apps.companies.selectors.company_selectors import get_company_by_id
from apps.locations.models import Location
from apps.locations.selectors.location_selectors import (
    get_location_by_id,
    get_locations_queryset,
)
from apps.locations.services.location_services import (
    deactivate_location,
    move_router_to_location,
    reactivate_location,
    safe_delete_location,
)
from apps.routers.models import Router
from apps.hotspot_sessions.models import HotspotSession
from .serializers import (
    LocationCreateUpdateSerializer,
    LocationDetailSerializer,
    LocationHotspotSummarySerializer,
    LocationListSerializer,
    LocationRouterSummarySerializer,
    LocationSessionSummarySerializer,
    MoveRouterSerializer,
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

    c = Company.objects.filter(memberships__user=request.user, memberships__is_active=True).first()
    if not c:
        c = Company.objects.first()
    return c


class LocationPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class LocationListCreateView(APIView):
    """
    GET  /api/v1/locations/ — List locations with aggregated metrics & filters
    POST /api/v1/locations/ — Create a new location under tenant company
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = _get_request_company(request)
        if not company:
            return Response({'detail': 'Company not found.'}, status=status.HTTP_404_NOT_FOUND)

        filters = {
            'status': request.query_params.get('status'),
            'site_type': request.query_params.get('site_type'),
            'region': request.query_params.get('region'),
            'district': request.query_params.get('district'),
            'is_active': request.query_params.get('is_active'),
            'search': request.query_params.get('search'),
            'ordering': request.query_params.get('ordering', 'name'),
        }

        qs = get_locations_queryset(company=company, filters=filters)

        # Optional pagination support
        if request.query_params.get('paginate', '').lower() == 'true' or request.query_params.get('page'):
            paginator = LocationPagination()
            page = paginator.paginate_queryset(qs, request)
            serializer = LocationListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = LocationListSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        company = _get_request_company(request)
        if not company:
            return Response({'detail': 'Company not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = LocationCreateUpdateSerializer(data=request.data, context={'company': company})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        location = serializer.save()

        AuditLog.objects.create(
            company=company,
            user=request.user,
            action='LOCATION_CREATED',
            resource_type='Location',
            resource_id=str(location.id),
            changes={
                'name': location.name,
                'code': location.code,
                'region': location.region,
                'status': location.status,
                'site_type': location.site_type,
            }
        )

        return Response(LocationDetailSerializer(location).data, status=status.HTTP_201_CREATED)


class LocationDetailView(APIView):
    """
    GET    /api/v1/locations/<id>/ — Retrieve location detail
    PATCH  /api/v1/locations/<id>/ — Update location
    DELETE /api/v1/locations/<id>/ — Deactivate (if in use) or delete location
    """
    permission_classes = [IsAuthenticated]

    def _get_location(self, location_id, request) -> Optional[Location]:
        company = _get_request_company(request)
        if not company:
            return None
        return get_location_by_id(location_id=location_id, company=company)

    def get(self, request, location_id):
        location = self._get_location(location_id, request)
        if not location:
            return Response({'detail': 'Location not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(LocationDetailSerializer(location).data, status=status.HTTP_200_OK)

    def patch(self, request, location_id):
        location = self._get_location(location_id, request)
        if not location:
            return Response({'detail': 'Location not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = LocationCreateUpdateSerializer(
            location,
            data=request.data,
            partial=True,
            context={'company': location.company}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        updated_location = serializer.save()

        AuditLog.objects.create(
            company=location.company,
            user=request.user,
            action='LOCATION_UPDATED',
            resource_type='Location',
            resource_id=str(location.id),
            changes=serializer.validated_data
        )

        return Response(LocationDetailSerializer(updated_location).data, status=status.HTTP_200_OK)

    def delete(self, request, location_id):
        location = self._get_location(location_id, request)
        if not location:
            return Response({'detail': 'Location not found.'}, status=status.HTTP_404_NOT_FOUND)

        action, message = safe_delete_location(location=location, user=request.user)
        return Response({'action': action, 'detail': message}, status=status.HTTP_200_OK)


class LocationReactivateView(APIView):
    """
    POST /api/v1/locations/<id>/reactivate/ — Reactivate a previously archived location
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, location_id):
        company = _get_request_company(request)
        location = get_location_by_id(location_id=location_id, company=company)
        if not location:
            return Response({'detail': 'Location not found.'}, status=status.HTTP_404_NOT_FOUND)

        reactivate_location(location=location, user=request.user)
        return Response({
            'action': 'reactivated',
            'detail': f"Location '{location.name}' reactivated.",
            'location': LocationDetailSerializer(location).data,
        }, status=status.HTTP_200_OK)


class LocationRoutersView(APIView):
    """
    GET /api/v1/locations/<id>/routers/ — List routers deployed at this location
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, location_id):
        company = _get_request_company(request)
        location = get_location_by_id(location_id=location_id, company=company)
        if not location:
            return Response({'detail': 'Location not found.'}, status=status.HTTP_404_NOT_FOUND)

        routers = location.routers.all().order_by('name')
        serializer = LocationRouterSummarySerializer(routers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LocationHotspotsView(APIView):
    """
    GET /api/v1/locations/<id>/hotspots/ — List hotspots operating at this location
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, location_id):
        company = _get_request_company(request)
        location = get_location_by_id(location_id=location_id, company=company)
        if not location:
            return Response({'detail': 'Location not found.'}, status=status.HTTP_404_NOT_FOUND)

        hotspots = location.hotspots.select_related('router').prefetch_related('plans').order_by('name')
        serializer = LocationHotspotSummarySerializer(hotspots, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LocationSessionsView(APIView):
    """
    GET /api/v1/locations/<id>/sessions/ — List active sessions under this location
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, location_id):
        company = _get_request_company(request)
        location = get_location_by_id(location_id=location_id, company=company)
        if not location:
            return Response({'detail': 'Location not found.'}, status=status.HTTP_404_NOT_FOUND)

        qs = HotspotSession.objects.filter(hotspot__location=location).select_related('hotspot', 'entitlement')
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter.strip().upper())
        else:
            qs = qs.filter(status='ACTIVE')

        serializer = LocationSessionSummarySerializer(qs.order_by('-started_at')[:100], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LocationMoveRouterView(APIView):
    """
    POST /api/v1/locations/<id>/move-router/ — Move router and hosted hotspots to this location
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, location_id):
        company = _get_request_company(request)
        location = get_location_by_id(location_id=location_id, company=company)
        if not location:
            return Response({'detail': 'Location not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = MoveRouterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        router_id = serializer.validated_data['router_id']
        router = Router.objects.filter(id=router_id, company=company).first()
        if not router:
            return Response({'detail': 'Router not found or belongs to another company.'}, status=status.HTTP_404_NOT_FOUND)

        updated_router = move_router_to_location(
            router=router,
            new_location=location,
            user=request.user
        )

        return Response({
            'action': 'moved',
            'detail': f"Router '{updated_router.name}' moved to location '{location.name}'.",
            'router_id': str(updated_router.id),
            'location_id': str(location.id),
        }, status=status.HTTP_200_OK)