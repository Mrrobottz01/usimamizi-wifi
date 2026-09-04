from django.core.paginator import Paginator
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.companies.permissions import IsCompanyMember
from apps.companies.selectors.company_selectors import get_company_by_id

from ..models import HotspotSession, SessionDisconnectTrigger
from ..selectors.session_selectors import (
    calculate_session_summary_metrics,
    get_sessions_queryset,
)
from ..services.session_control import disconnect_hotspot_session
from .serializers import (
    HotspotSessionSerializer,
    ManualDisconnectSerializer,
    SessionDisconnectRequestSerializer,
)


class HotspotSessionListView(APIView):
    """
    GET /api/v1/sessions/?company_id={uuid}
    List active and historical network connection sessions with metrics and pagination.
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
            'entitlement_id': request.query_params.get('entitlement_id'),
            'mac_address': request.query_params.get('mac_address'),
            'search': request.query_params.get('search'),
            'sort_by': request.query_params.get('sort_by', '-started_at'),
        }

        qs = get_sessions_queryset(company=company, filters=filters)

        page_num = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('page_size', 20)), 100)

        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page_num)

        summary = calculate_session_summary_metrics(company=company, queryset=qs)
        serializer = HotspotSessionSerializer(page_obj.object_list, many=True)

        return Response({
            "results": serializer.data,
            "count": paginator.count,
            "page": page_num,
            "page_size": page_size,
            "total_pages": paginator.num_pages,
            "summary": summary
        }, status=status.HTTP_200_OK)


class HotspotSessionDetailView(APIView):
    """
    GET /api/v1/sessions/{id}/?company_id={uuid}
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

        session = HotspotSession.objects.filter(id=id, company=company).select_related(
            'entitlement', 'entitlement__plan', 'radius_client'
        ).first()

        if not session:
            return Response({"code": "not_found", "detail": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(HotspotSessionSerializer(session).data, status=status.HTTP_200_OK)


class SessionDisconnectView(APIView):
    """
    POST /api/v1/sessions/{id}/disconnect/?company_id={uuid}
    Dispatch a RADIUS Disconnect-Request (RFC 3576) to immediately terminate an active session.
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def post(self, request, id):
        company_id = request.query_params.get('company_id')
        if not company_id:
            return Response({"code": "missing_company_id", "detail": "'company_id' is required."}, status=status.HTTP_400_BAD_REQUEST)

        company = get_company_by_id(company_id)
        if not company:
            return Response({"code": "company_not_found", "detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, company)

        session = HotspotSession.objects.filter(id=id, company=company).first()
        if not session:
            return Response({"code": "not_found", "detail": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ManualDisconnectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data['reason']

        disconnect_req = disconnect_hotspot_session(
            session=session,
            trigger_type=SessionDisconnectTrigger.MANUAL,
            reason=reason,
            requested_by=request.user
        )

        return Response({
            "disconnect_request_id": str(disconnect_req.id),
            "status": disconnect_req.status,
            "response_code": disconnect_req.response_code,
            "response_message": disconnect_req.response_message,
            "last_error": disconnect_req.last_error,
            "attempt_count": disconnect_req.attempt_count,
        }, status=status.HTTP_200_OK)


class SessionDisconnectHistoryView(APIView):
    """
    GET /api/v1/sessions/{id}/disconnect-history/?company_id={uuid}
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

        session = HotspotSession.objects.filter(id=id, company=company).first()
        if not session:
            return Response({"code": "not_found", "detail": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

        reqs = session.disconnect_requests.all().order_by('-requested_at')
        return Response(SessionDisconnectRequestSerializer(reqs, many=True).data, status=status.HTTP_200_OK)
