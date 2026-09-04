from datetime import datetime, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APIClient

from apps.companies.services.company_services import create_company
from apps.entitlements.exceptions import InvalidEntitlementStateTransition
from apps.entitlements.models import (
    AccessEntitlement,
    EntitlementSourceType,
    EntitlementStatus,
)
from apps.entitlements.services.entitlement_services import (
    activate_entitlement,
    add_months_to_date,
    calculate_entitlement_validity,
    create_entitlement_from_plan,
    grant_manual_entitlement,
    is_entitlement_authorizable,
    resume_entitlement,
    revoke_entitlement,
    suspend_entitlement,
)
from apps.entitlements.tasks import expire_due_entitlements
from apps.plans.models import DurationUnit, ValidityMode
from apps.plans.services.plan_services import create_plan
from apps.vouchers.models import VoucherStatus
from apps.vouchers.services.voucher_services import (
    generate_voucher_batch,
    redeem_voucher,
)

User = get_user_model()


@pytest.fixture
def entitlement_setup():
    user1 = User.objects.create_user(email='admin_ent1@example.com', password='Password123!')
    company1 = create_company(name='Company Alpha', user=user1)

    user2 = User.objects.create_user(email='admin_ent2@example.com', password='Password123!')
    company2 = create_company(name='Company Beta', user=user2)

    plan1 = create_plan(
        company=company1,
        data={
            'name': '24 Hour Turbo',
            'code': 'ALPHA-24H',
            'price': '3000.00',
            'duration_value': 24,
            'duration_unit': DurationUnit.HOURS,
            'validity_mode': ValidityMode.CONTINUOUS,
            'download_speed_kbps': 5120,
            'upload_speed_kbps': 2048,
            'data_limit_bytes': 1073741824,  # 1 GB
        }
    )

    plan2 = create_plan(
        company=company2,
        data={
            'name': 'Beta Basic',
            'code': 'BETA-1H',
            'price': '1000.00',
            'duration_value': 1,
            'duration_unit': DurationUnit.HOURS,
            'validity_mode': ValidityMode.CONTINUOUS,
        }
    )

    return {
        'user1': user1,
        'company1': company1,
        'user2': user2,
        'company2': company2,
        'plan1': plan1,
        'plan2': plan2,
    }


@pytest.mark.django_db
def test_plan_snapshot_immutability(entitlement_setup):
    """
    Test that plan snapshots on AccessEntitlement remain immutable even if the original Plan is modified.
    """
    plan = entitlement_setup['plan1']
    company = entitlement_setup['company1']

    batch, vouchers = generate_voucher_batch(
        company=company,
        plan=plan,
        quantity=1,
        created_by=entitlement_setup['user1']
    )
    voucher = vouchers[0]

    # Redeem voucher -> creates entitlement
    _, entitlement = redeem_voucher(voucher_code=voucher.display_code, company=company)

    assert entitlement.download_speed_kbps == 5120
    assert entitlement.upload_speed_kbps == 2048
    assert entitlement.plan_snapshot['price'] == '3000.00'
    assert entitlement.plan_snapshot['plan_name'] == '24 Hour Turbo'

    # Modify original plan
    plan.name = 'Updated Mega Plan'
    plan.download_speed_kbps = 10240
    plan.upload_speed_kbps = 5120
    plan.price = 5000.00
    plan.save()

    # Refresh entitlement from DB
    entitlement.refresh_from_db()
    assert entitlement.download_speed_kbps == 5120  # Unchanged
    assert entitlement.upload_speed_kbps == 2048    # Unchanged
    assert entitlement.plan_snapshot['price'] == '3000.00'  # Unchanged
    assert entitlement.plan_snapshot['plan_name'] == '24 Hour Turbo'  # Unchanged

    # New entitlement receives updated values
    batch2, vouchers2 = generate_voucher_batch(
        company=company,
        plan=plan,
        quantity=1,
        created_by=entitlement_setup['user1']
    )
    _, entitlement2 = redeem_voucher(voucher_code=vouchers2[0].display_code, company=company)
    assert entitlement2.download_speed_kbps == 10240
    assert entitlement2.upload_speed_kbps == 5120
    assert entitlement2.plan_snapshot['price'] == '5000.00'


@pytest.mark.django_db
def test_voucher_atomicity_and_concurrency(entitlement_setup):
    """
    Test that voucher redemption creates exactly one entitlement atomically and enforces 1-to-1 DB constraints.
    """
    plan = entitlement_setup['plan1']
    company = entitlement_setup['company1']

    _, vouchers = generate_voucher_batch(
        company=company,
        plan=plan,
        quantity=1,
        created_by=entitlement_setup['user1']
    )
    voucher = vouchers[0]

    redeemed_v, entitlement = redeem_voucher(
        voucher_code=voucher.display_code,
        company=company,
        customer_phone='+255757047012'
    )

    assert redeemed_v.status == VoucherStatus.REDEEMED
    assert entitlement.status == EntitlementStatus.ACTIVE
    assert entitlement.voucher_id == voucher.id
    assert entitlement.reference.startswith('ENT-')

    # Double redemption attempt is strictly blocked
    with pytest.raises(ValidationError):
        redeem_voucher(voucher_code=voucher.display_code, company=company)

    # Entitlement count remains exactly 1
    assert AccessEntitlement.objects.filter(voucher=voucher).count() == 1


@pytest.mark.django_db
def test_entitlement_lifecycle_transitions(entitlement_setup):
    """
    Test valid and invalid lifecycle state transitions:
    PENDING -> ACTIVE -> SUSPENDED -> ACTIVE -> REVOKED.
    """
    company = entitlement_setup['company1']
    plan = entitlement_setup['plan1']
    user = entitlement_setup['user1']

    # Create PENDING entitlement
    entitlement = create_entitlement_from_plan(
        company=company,
        plan=plan,
        source_type=EntitlementSourceType.MANUAL,
        activate_immediately=False
    )
    assert entitlement.status == EntitlementStatus.PENDING

    # 1. PENDING -> ACTIVE
    activated = activate_entitlement(entitlement=entitlement)
    assert activated.status == EntitlementStatus.ACTIVE
    assert activated.activated_at is not None

    # Invalid: Activate already active
    with pytest.raises(InvalidEntitlementStateTransition):
        activate_entitlement(entitlement=activated)

    # 2. ACTIVE -> SUSPENDED
    suspended = suspend_entitlement(entitlement=activated, actor=user, reason='Non-payment')
    assert suspended.status == EntitlementStatus.SUSPENDED
    assert suspended.suspended_at is not None
    assert suspended.suspended_by == user
    assert suspended.suspension_reason == 'Non-payment'

    # Invalid: Suspend already suspended
    with pytest.raises(InvalidEntitlementStateTransition):
        suspend_entitlement(entitlement=suspended, actor=user)

    # 3. SUSPENDED -> ACTIVE (Resume)
    resumed = resume_entitlement(entitlement=suspended, actor=user)
    assert resumed.status == EntitlementStatus.ACTIVE
    assert resumed.suspended_at is None
    assert resumed.suspended_by is None

    # 4. ACTIVE -> REVOKED
    revoked = revoke_entitlement(entitlement=resumed, actor=user, reason='Policy violation')
    assert revoked.status == EntitlementStatus.REVOKED
    assert revoked.revoked_at is not None
    assert revoked.revocation_reason == 'Policy violation'

    # Invalid: Resume or Activate a REVOKED entitlement
    with pytest.raises(InvalidEntitlementStateTransition):
        resume_entitlement(entitlement=revoked, actor=user)

    with pytest.raises(InvalidEntitlementStateTransition):
        activate_entitlement(entitlement=revoked)


@pytest.mark.django_db
def test_validity_modes_and_calendar_math(entitlement_setup):
    """
    Test CONTINUOUS, CALENDAR, and USAGE_TIME validity calculations, including month boundaries.
    """
    company = entitlement_setup['company1']
    now = timezone.now()

    # 1. CONTINUOUS — 2 hours
    plan_cont = create_plan(
        company=company,
        data={
            'name': '2 Hours Continuous',
            'code': 'CONT-2H',
            'price': '1000.00',
            'duration_value': 2,
            'duration_unit': DurationUnit.HOURS,
            'validity_mode': ValidityMode.CONTINUOUS,
        }
    )
    v_from, expires_at, usage_sec = calculate_entitlement_validity(plan_cont, now)
    assert v_from == now
    assert expires_at == now + timedelta(hours=2)
    assert usage_sec is None

    # 2. CALENDAR — Month addition boundary test (Jan 31 + 1 month -> Feb 28 in non-leap year)
    from datetime import timezone as dt_tz
    jan_31 = datetime(2025, 1, 31, 12, 0, 0, tzinfo=dt_tz.utc)
    feb_date = add_months_to_date(jan_31, 1)
    assert feb_date.year == 2025
    assert feb_date.month == 2
    assert feb_date.day == 28

    # 3. USAGE_TIME — 5 hours
    plan_usage = create_plan(
        company=company,
        data={
            'name': '5 Hours Usage Time',
            'code': 'USAGE-5H',
            'price': '2500.00',
            'duration_value': 5,
            'duration_unit': DurationUnit.HOURS,
            'validity_mode': ValidityMode.USAGE_TIME,
        }
    )
    v_from, expires_at, usage_sec = calculate_entitlement_validity(plan_usage, now)
    assert usage_sec == 5 * 3600  # 18000 seconds
    assert expires_at is not None


@pytest.mark.django_db
def test_data_quota_and_usage_time_authorizability(entitlement_setup):
    """
    Test authorizability decisions for data quotas, usage time quotas, suspension, revocation, and expiry.
    """
    company = entitlement_setup['company1']
    plan = entitlement_setup['plan1']

    entitlement = create_entitlement_from_plan(
        company=company,
        plan=plan,
        source_type=EntitlementSourceType.MANUAL,
        activate_immediately=True
    )

    # Initially ACTIVE and valid
    auth_ok, reason = is_entitlement_authorizable(entitlement)
    assert auth_ok is True
    assert reason == 'AUTHORIZED'

    # Exhaust Data Quota
    entitlement.data_used_bytes = entitlement.data_limit_bytes
    entitlement.save()
    auth_ok, reason = is_entitlement_authorizable(entitlement)
    assert auth_ok is False
    assert reason == 'DATA_QUOTA_EXHAUSTED'

    # Reset Data Quota
    entitlement.data_used_bytes = 1000
    entitlement.save()

    # Exhaust Usage Time (if set)
    entitlement.usage_time_limit_seconds = 3600
    entitlement.usage_time_used_seconds = 3600
    entitlement.save()
    auth_ok, reason = is_entitlement_authorizable(entitlement)
    assert auth_ok is False
    assert reason == 'USAGE_TIME_EXHAUSTED'

    entitlement.usage_time_limit_seconds = None
    entitlement.save()

    # Suspended Entitlement
    suspend_entitlement(entitlement=entitlement, reason='Investigation')
    auth_ok, reason = is_entitlement_authorizable(entitlement)
    assert auth_ok is False
    assert reason == 'SUSPENDED'

    # Resumed Entitlement
    resume_entitlement(entitlement=entitlement)
    auth_ok, reason = is_entitlement_authorizable(entitlement)
    assert auth_ok is True

    # Revoked Entitlement
    revoke_entitlement(entitlement=entitlement, reason='Fraudulent payment')
    auth_ok, reason = is_entitlement_authorizable(entitlement)
    assert auth_ok is False
    assert reason == 'REVOKED'


@pytest.mark.django_db
def test_manual_grant_service_and_api(entitlement_setup):
    """
    Test manual access grant endpoint and mandatory reason validation.
    """
    client = APIClient()
    user = entitlement_setup['user1']
    company = entitlement_setup['company1']
    plan = entitlement_setup['plan1']
    client.force_authenticate(user=user)

    # 1. Missing reason -> 400 Bad Request
    res = client.post(
        '/api/v1/entitlements/manual-grant/',
        data={
            'company_id': str(company.id),
            'plan_id': str(plan.id),
            'reason': ''
        },
        format='json'
    )
    assert res.status_code == 400

    # 2. Valid grant
    res_ok = client.post(
        '/api/v1/entitlements/manual-grant/',
        data={
            'company_id': str(company.id),
            'plan_id': str(plan.id),
            'reason': 'Complimentary access for VIP hotel guest'
        },
        format='json'
    )
    assert res_ok.status_code == 201
    data = res_ok.data
    assert data['reference'].startswith('ENT-')
    assert data['source_type'] == 'MANUAL'
    assert data['status'] == 'ACTIVE'
    assert data['is_authorizable'] is True


@pytest.mark.django_db
def test_expire_due_entitlements_celery_task(entitlement_setup):
    """
    Test periodic expiry task, bounded batch processing, and idempotency.
    """
    company = entitlement_setup['company1']
    plan = entitlement_setup['plan1']

    # Create active entitlement that expired 1 hour ago
    past_time = timezone.now() - timedelta(hours=1)
    ent_expired = create_entitlement_from_plan(
        company=company,
        plan=plan,
        source_type=EntitlementSourceType.MANUAL,
        activate_immediately=True
    )
    ent_expired.expires_at = past_time
    ent_expired.save()

    # Create active entitlement that expires in 24 hours
    ent_future = create_entitlement_from_plan(
        company=company,
        plan=plan,
        source_type=EntitlementSourceType.MANUAL,
        activate_immediately=True
    )

    # Run expiry task
    count1 = expire_due_entitlements(batch_size=100)
    assert count1 == 1

    ent_expired.refresh_from_db()
    ent_future.refresh_from_db()
    assert ent_expired.status == EntitlementStatus.EXPIRED
    assert ent_future.status == EntitlementStatus.ACTIVE

    # Run again -> Idempotent, 0 processed
    count2 = expire_due_entitlements(batch_size=100)
    assert count2 == 0


@pytest.mark.django_db
def test_entitlements_api_and_tenant_isolation(entitlement_setup):
    """
    Test strict multi-tenant boundary on entitlements API (List, Detail, Suspend, Resume, Revoke).
    """
    client = APIClient()
    user1 = entitlement_setup['user1']
    company1 = entitlement_setup['company1']
    plan1 = entitlement_setup['plan1']

    user2 = entitlement_setup['user2']

    # User 1 creates entitlement for Company 1
    ent1 = grant_manual_entitlement(
        company=company1,
        plan=plan1,
        actor=user1,
        reason='Alpha staff testing'
    )

    # User 2 logs in
    client.force_authenticate(user=user2)

    # User 2 cannot list Company 1 entitlements
    res_list = client.get(f'/api/v1/entitlements/?company_id={company1.id}')
    assert res_list.status_code == 403

    # User 2 cannot retrieve Company 1 entitlement details
    res_detail = client.get(f'/api/v1/entitlements/{ent1.id}/?company_id={company1.id}')
    assert res_detail.status_code == 403

    # User 2 cannot suspend Company 1 entitlement
    res_susp = client.post(
        f'/api/v1/entitlements/{ent1.id}/suspend/',
        data={'company_id': str(company1.id), 'reason': 'Attack'},
        format='json'
    )
    assert res_susp.status_code == 403

    # User 2 cannot revoke Company 1 entitlement
    res_rev = client.post(
        f'/api/v1/entitlements/{ent1.id}/revoke/',
        data={'company_id': str(company1.id), 'reason': 'Attack'},
        format='json'
    )
    assert res_rev.status_code == 403
