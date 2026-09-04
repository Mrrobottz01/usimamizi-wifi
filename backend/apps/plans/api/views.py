from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.companies.permissions import IsCompanyMember
from apps.companies.selectors.company_selectors import get_company_by_id

from ..selectors.plan_selectors import get_plan_by_id, get_plans_for_company
from ..services.plan_services import create_plan, deactivate_plan, update_plan
from .serializers import PlanCreateUpdateSerializer, PlanSerializer


class PlanListCreateView(APIView):
    """
    GET  /api/v1/plans/?company_id={uuid} — List plans for company
    POST /api/v1/plans/ — Create a new plan for company
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get(self, request):
        company_id = request.query_params.get('company_id')
        if not company_id:
            return Response(
                {"code": "missing_company_id", "detail": "query parameter 'company_id' is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        company = get_company_by_id(company_id)
        if not company:
            return Response(
                {"code": "company_not_found", "detail": "Company not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        self.check_object_permissions(request, company)

        include_inactive = request.query_params.get('include_inactive', 'false').lower() == 'true'
        plans = get_plans_for_company(company, include_inactive=include_inactive)
        serializer = PlanSerializer(plans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        company_id = request.data.get('company_id') or request.query_params.get('company_id')
        if not company_id:
            return Response(
                {"code": "missing_company_id", "detail": "'company_id' is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        company = get_company_by_id(company_id)
        if not company:
            return Response(
                {"code": "company_not_found", "detail": "Company not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        self.check_object_permissions(request, company)

        serializer = PlanCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            plan = create_plan(company=company, data=serializer.validated_data)
            return Response(PlanSerializer(plan).data, status=status.HTTP_201_CREATED)
        except ValidationError as err:
            return Response(
                {"code": "validation_error", "detail": "Plan validation failed.", "field_errors": err.message_dict if hasattr(err, 'message_dict') else {'detail': err.messages}},
                status=status.HTTP_400_BAD_REQUEST
            )


class PlanDetailView(APIView):
    """
    GET   /api/v1/plans/{id}/ — Retrieve plan details
    PATCH /api/v1/plans/{id}/ — Update plan
    DELETE /api/v1/plans/{id}/ — Deactivate plan
    """
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get(self, request, plan_id):
        plan = get_plan_by_id(plan_id)
        if not plan:
            return Response({"code": "plan_not_found", "detail": "Plan not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, plan.company)
        return Response(PlanSerializer(plan).data, status=status.HTTP_200_OK)

    def patch(self, request, plan_id):
        plan = get_plan_by_id(plan_id)
        if not plan:
            return Response({"code": "plan_not_found", "detail": "Plan not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, plan.company)

        serializer = PlanCreateUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            updated = update_plan(plan=plan, data=serializer.validated_data)
            return Response(PlanSerializer(updated).data, status=status.HTTP_200_OK)
        except ValidationError as err:
            return Response(
                {"code": "validation_error", "detail": "Plan update failed.", "field_errors": err.message_dict if hasattr(err, 'message_dict') else {'detail': err.messages}},
                status=status.HTTP_400_BAD_REQUEST
            )

    def delete(self, request, plan_id):
        plan = get_plan_by_id(plan_id)
        if not plan:
            return Response({"code": "plan_not_found", "detail": "Plan not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, plan.company)
        deactivated = deactivate_plan(plan=plan)
        return Response(PlanSerializer(deactivated).data, status=status.HTTP_200_OK)
