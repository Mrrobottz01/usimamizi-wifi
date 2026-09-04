from django.db import transaction
from django.utils.text import slugify

from ..models import Company, CompanyMembership, CompanyStatus


@transaction.atomic
def create_company(*, name: str, user, slug: str = None, country: str = 'TZ', currency: str = 'TZS', timezone: str = 'Africa/Dar_es_Salaam') -> Company:
    """
    Create a new company and automatically grant active membership to the creating user.
    """
    if not slug:
        base_slug = slugify(name)
        slug = base_slug
        count = 1
        while Company.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{count}"
            count += 1

    company = Company.objects.create(
        name=name,
        slug=slug,
        country=country,
        currency=currency,
        timezone=timezone,
        status=CompanyStatus.ACTIVE
    )

    CompanyMembership.objects.create(
        company=company,
        user=user,
        is_active=True
    )

    return company


@transaction.atomic
def add_company_member(*, company: Company, user, is_active: bool = True) -> CompanyMembership:
    """
    Add or activate a membership for a user in a company.
    """
    membership, created = CompanyMembership.objects.get_or_create(
        company=company,
        user=user,
        defaults={'is_active': is_active}
    )
    if not created and membership.is_active != is_active:
        membership.is_active = is_active
        membership.save(update_fields=['is_active'])
    return membership
