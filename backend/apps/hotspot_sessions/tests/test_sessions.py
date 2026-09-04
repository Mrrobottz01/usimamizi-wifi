import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.companies.services.company_services import create_company
from apps.entitlements.models import EntitlementSourceType
from apps.entitlements.services.entitlement_services import create_entitlement_from_plan
from apps.hotspot_sessions.models import HotspotSession, SessionStatus
from apps.plans.models import DurationUnit, ValidityMode
from apps.plans.services.plan_services import create_plan

User = get_user_model()


@pytest.fixture
def session_setup():
    user1 = User.objects.create_user(email='sess_alpha@example.com', password='Password123!')
    company1 = create_company(name='Session Alpha Co', user=user1)

    user2 = User.objects.create_user(email='sess_beta@example.com', password='Password123!')
    company2 = create_company(name='Session Beta Co', user=user2)

    plan1 = create_plan(
        company=company1,
        data={
            'name': 'Session Plan 1',
            'code': 'SESS-1',
            'price': '1000.00',
            'duration_value': 1,
            'duration_unit': DurationUnit.HOURS,
            'validity_mode': ValidityMode.CONTINUOUS,
        }
    )

    ent1 = create_entitlement_from_plan(
        company=company1,
        plan=plan1,
        source_type=EntitlementSourceType.MANUAL,
        activate_immediately=True
    )

    sess1 = HotspotSession.objects.create(
        company=company1,
        entitlement=ent1,
        acct_session_id='sess_test_1',
        username=ent1.reference,
        mac_address='AA:BB:CC:11:22:33',
        ip_address='10.5.50.120',
        status=SessionStatus.ACTIVE,
        input_bytes=1000000,
        output_bytes=5000000,
        session_seconds=300
    )

    return {
        'company1': company1,
        'company2': company2,
        'user1': user1,
        'user2': user2,
        'sess1': sess1,
        'ent1': ent1,
    }


@pytest.mark.django_db
def test_sessions_list_and_metrics_api(session_setup):
    """
    Test GET /api/v1/sessions/ endpoint with summary metrics and pagination.
    """
    client = APIClient()
    user = session_setup['user1']
    company = session_setup['company1']
    client.force_authenticate(user=user)

    res = client.get(f'/api/v1/sessions/?company_id={company.id}')
    assert res.status_code == 200
    data = res.data

    assert data['count'] == 1
    assert data['summary']['active'] == 1
    assert data['results'][0]['acct_session_id'] == 'sess_test_1'
    assert data['results'][0]['mac_address'] == 'AA:BB:CC:11:22:33'
    assert data['results'][0]['total_bytes'] == 6000000


@pytest.mark.django_db
def test_sessions_tenant_isolation(session_setup):
    """
    Test that Company B cannot view Company A's hotspot sessions.
    """
    client = APIClient()
    user2 = session_setup['user2']
    company1 = session_setup['company1']
    sess1 = session_setup['sess1']
    client.force_authenticate(user=user2)

    # Cannot list Company 1 sessions
    res_list = client.get(f'/api/v1/sessions/?company_id={company1.id}')
    assert res_list.status_code == 403

    # Cannot get Company 1 session details
    res_detail = client.get(f'/api/v1/sessions/{sess1.id}/?company_id={company1.id}')
    assert res_detail.status_code == 403
