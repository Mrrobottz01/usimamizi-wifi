from typing import Optional

from django.db.models import QuerySet

from apps.companies.models import Company

from ..models import Plan


def get_plans_for_company(company: Company, include_inactive: bool = False) -> QuerySet[Plan]:
    """
    Retrieve all plans belonging to a company.
    """
    qs = Plan.objects.filter(company=company)
    if not include_inactive:
        qs = qs.filter(is_active=True)
    return qs.order_by('sort_order', 'name')


def get_plan_by_id(plan_id: str, company: Optional[Company] = None) -> Optional[Plan]:
    """
    Retrieve a plan by ID, optionally enforcing company boundary.
    """
    try:
        qs = Plan.objects.all()
        if company:
            qs = qs.filter(company=company)
        return qs.get(id=plan_id)
    except (Plan.DoesNotExist, ValueError):
        return None
