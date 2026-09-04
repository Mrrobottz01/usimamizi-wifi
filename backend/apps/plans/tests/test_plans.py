from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.companies.services.company_services import create_company
from apps.plans.services.plan_services import create_plan

User = get_user_model()


@pytest.mark.django_db
def test_create_plan_service_validation():
    user = User.objects.create_user(email='owner_plan@example.com', password='Password123!')
    company = create_company(name='Plan Co', user=user)

    # Valid creation
    plan_data = {
        'name': '1 Hour Pass',
        'code': '1H-PASS',
        'price': '1000.00',
        'currency': 'TZS',
        'duration_value': 1,
        'duration_unit': 'HOURS',
        'download_speed_kbps': 10000,
        'upload_speed_kbps': 3000,
        'max_devices': 1,
    }
    plan = create_plan(company=company, data=plan_data)
    assert plan.name == '1 Hour Pass'
    assert plan.price == Decimal('1000.00')
    assert plan.is_active is True

    # Negative price validation
    with pytest.raises(ValidationError):
        create_plan(company=company, data={**plan_data, 'code': 'NEW-CODE', 'price': '-500.00'})

    # Duplicate code for same company
    with pytest.raises(ValidationError):
        create_plan(company=company, data=plan_data)


@pytest.mark.django_db
def test_plan_api_tenant_isolation():
    user1 = User.objects.create_user(email='user1_plan@example.com', password='Password123!')
    company1 = create_company(name='Company A', user=user1)

    user2 = User.objects.create_user(email='user2_plan@example.com', password='Password123!')
    create_company(name='Company B', user=user2)

    plan1 = create_plan(company=company1, data={'name': 'Plan A', 'code': 'PL-A', 'price': '2000.00'})

    client = APIClient()

    # User 1 accesses Company 1 plan -> 200 OK
    client.force_authenticate(user=user1)
    res = client.get(f'/api/v1/plans/{plan1.id}/')
    assert res.status_code == 200
    assert res.data['name'] == 'Plan A'

    # User 2 attempts to access Company 1 plan -> 403 Forbidden
    client.force_authenticate(user=user2)
    res_forbidden = client.get(f'/api/v1/plans/{plan1.id}/')
    assert res_forbidden.status_code == 403
