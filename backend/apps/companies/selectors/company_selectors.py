from typing import Optional

from django.db.models import QuerySet

from ..models import Company


def get_user_companies(user) -> QuerySet[Company]:
    """
    Returns QuerySet of companies that the user has an active membership in.
    Guarantees tenant boundaries at query level.
    """
    if not user.is_authenticated:
        return Company.objects.none()

    if user.is_superuser:
        return Company.objects.all()

    return Company.objects.filter(
        memberships__user=user,
        memberships__is_active=True
    ).distinct()


def get_company_by_id_for_user(user, company_id: str) -> Optional[Company]:
    """
    Fetch a single company by ID ensuring user has active membership.
    Returns None if user is not authorized or company does not exist.
    """
    qs = get_user_companies(user)
    try:
        return qs.get(id=company_id)
    except Company.DoesNotExist:
        return None


def get_company_by_id(company_id: str) -> Optional[Company]:
    """
    Fetch a single company by ID.
    """
    try:
        return Company.objects.get(id=company_id)
    except (Company.DoesNotExist, ValueError):
        return None

