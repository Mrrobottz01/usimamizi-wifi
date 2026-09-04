from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..selectors.company_selectors import get_company_by_id_for_user, get_user_companies
from ..services.company_services import create_company
from .serializers import CompanySerializer


class CompanyListView(APIView):
    """
    GET /api/v1/companies/
    POST /api/v1/companies/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        companies = get_user_companies(request.user)
        serializer = CompanySerializer(companies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CompanySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        company = create_company(
            name=serializer.validated_data['name'],
            user=request.user,
            slug=serializer.validated_data.get('slug'),
            country=serializer.validated_data.get('country', 'TZ'),
            currency=serializer.validated_data.get('currency', 'TZS'),
            timezone=serializer.validated_data.get('timezone', 'Africa/Dar_es_Salaam')
        )
        output_serializer = CompanySerializer(company)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class CompanyDetailView(APIView):
    """
    GET /api/v1/companies/{id}/
    Guarantees strict tenant isolation. Cross-tenant access is denied.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        company = get_company_by_id_for_user(request.user, str(pk))
        if not company:
            # Enforce security boundary: Cross-tenant attempts return 403 Forbidden
            raise PermissionDenied("You do not have permission to access this company.")

        serializer = CompanySerializer(company)
        return Response(serializer.data, status=status.HTTP_200_OK)
