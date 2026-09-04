import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.companies.services.company_services import create_company

User = get_user_model()


@pytest.mark.django_db
def test_tenant_isolation_boundary():
    user_a = User.objects.create_user(email='tenant_a@example.com', password='Password123!')
    user_b = User.objects.create_user(email='tenant_b@example.com', password='Password123!')

    company_a = create_company(name='Company A', user=user_a, slug='company-a')
    company_b = create_company(name='Company B', user=user_b, slug='company-b')

    client_a = APIClient()
    client_a.force_authenticate(user=user_a)

    client_b = APIClient()
    client_b.force_authenticate(user=user_b)

    # User A listing companies sees ONLY Company A
    res_a_list = client_a.get('/api/v1/companies/')
    assert res_a_list.status_code == 200
    company_ids_a = [c['id'] for c in res_a_list.data]
    assert str(company_a.id) in company_ids_a
    assert str(company_b.id) not in company_ids_a

    # User A accesses own Company A -> 200 OK
    res_a_own = client_a.get(f'/api/v1/companies/{company_a.id}/')
    assert res_a_own.status_code == 200
    assert res_a_own.data['name'] == 'Company A'

    # User A accesses Company B (Cross-Tenant) -> 403 Forbidden
    res_a_cross = client_a.get(f'/api/v1/companies/{company_b.id}/')
    assert res_a_cross.status_code == 403
    assert res_a_cross.data['code'] == 'PERMISSION_DENIED'

    # User B listing companies sees ONLY Company B
    res_b_list = client_b.get('/api/v1/companies/')
    assert res_b_list.status_code == 200
    company_ids_b = [c['id'] for c in res_b_list.data]
    assert str(company_b.id) in company_ids_b
    assert str(company_a.id) not in company_ids_b

    # User B accesses Company A (Cross-Tenant) -> 403 Forbidden
    res_b_cross = client_b.get(f'/api/v1/companies/{company_a.id}/')
    assert res_b_cross.status_code == 403
    assert res_b_cross.data['code'] == 'PERMISSION_DENIED'
