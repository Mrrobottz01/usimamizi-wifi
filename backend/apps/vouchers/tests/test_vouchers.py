import concurrent.futures
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.utils import timezone

from apps.companies.services.company_services import create_company
from apps.plans.services.plan_services import create_plan
from apps.vouchers.models import (
    Voucher,
    VoucherDistributionState,
    VoucherExportStatus,
    VoucherStatus,
)
from apps.vouchers.selectors.voucher_selectors import (
    get_voucher_metrics,
    get_voucher_timeline,
    normalize_voucher_code,
)
from apps.vouchers.services.voucher_services import (
    export_batch_csv,
    export_batch_routeros_script,
    generate_voucher_batch,
    get_printable_voucher_cards,
    redeem_voucher,
    reserve_voucher,
    revoke_voucher,
)

User = get_user_model()


@pytest.mark.django_db
def test_generate_voucher_batch_atomic_and_unique_codes():
    user = User.objects.create_user(email='batch_owner@example.com', password='Password123!')
    company = create_company(name='Voucher Co', user=user)
    plan = create_plan(company=company, data={'name': '1H Pass', 'code': 'LAB-1H', 'price': '1000.00'})

    batch, vouchers = generate_voucher_batch(
        company=company,
        plan=plan,
        quantity=10,
        created_by=user,
        label='Test Label',
        notes='Distribution notes',
        distribution_mode=VoucherDistributionState.SOLD
    )

    assert batch.quantity == 10
    assert batch.notes == 'Distribution notes'
    assert batch.distribution_mode == VoucherDistributionState.SOLD
    assert batch.export_status == VoucherExportStatus.NOT_EXPORTED
    assert len(vouchers) == 10
    codes = [v.display_code for v in vouchers]
    assert len(set(codes)) == 10  # All unique

    for v in vouchers:
        assert v.status == VoucherStatus.AVAILABLE
        assert v.distribution_state == VoucherDistributionState.SOLD
        assert v.export_status == VoucherExportStatus.NOT_EXPORTED
        assert len(v.display_code) == 9
        assert "-" in v.display_code
        assert v.code_hash is not None


@pytest.mark.django_db
def test_voucher_normalization():
    assert normalize_voucher_code('abcd-7xq9') == 'ABCD-7XQ9'
    assert normalize_voucher_code('abcd7xq9') == 'ABCD-7XQ9'
    assert normalize_voucher_code('  abcd 7xq9  ') == 'ABCD-7XQ9'
    assert normalize_voucher_code('ABCD-7XQ9') == 'ABCD-7XQ9'
    assert normalize_voucher_code('') == ''


@pytest.mark.django_db
def test_redeem_voucher_lifecycle_and_normalization():
    user = User.objects.create_user(email='redeem_owner@example.com', password='Password123!')
    company = create_company(name='Redeem Co', user=user)
    plan = create_plan(company=company, data={'name': 'Day Pass', 'code': 'LAB-DAY', 'price': '2000.00'})

    batch, vouchers = generate_voucher_batch(company=company, plan=plan, quantity=1, created_by=user)
    target_voucher = vouchers[0]

    # Redeem using unformatted lowercase code (e.g. abcd7xq9)
    raw_code = target_voucher.display_code.lower().replace('-', '')
    redeemed, entitlement = redeem_voucher(voucher_code=raw_code, company=company, customer_phone='+255712345678')
    assert redeemed.status == VoucherStatus.REDEEMED
    assert redeemed.redeemed_at is not None
    assert redeemed.redeemed_by_customer == '+255712345678'
    assert entitlement is not None
    assert entitlement.status == 'ACTIVE'
    assert entitlement.reference.startswith('ENT-')
    assert entitlement.voucher_id == target_voucher.id

    # Double redemption attempt -> Failure
    with pytest.raises(ValidationError) as exc:
        redeem_voucher(voucher_code=target_voucher.display_code, company=company)
    assert 'already been redeemed' in str(exc.value)


@pytest.mark.django_db
def test_reserve_voucher_lifecycle():
    user = User.objects.create_user(email='reserve_owner@example.com', password='Password123!')
    company = create_company(name='Reserve Co', user=user)
    plan = create_plan(company=company, data={'name': '1H Pass', 'code': 'LAB-1H', 'price': '1000.00'})

    batch, vouchers = generate_voucher_batch(company=company, plan=plan, quantity=1, created_by=user)
    voucher = vouchers[0]

    reserved = reserve_voucher(voucher=voucher, company=company, customer_phone='+255788112233', reserved_by=user)
    assert reserved.status == VoucherStatus.RESERVED
    assert reserved.reserved_at is not None
    assert reserved.recipient_phone == '+255788112233'

    # Reserved voucher can be redeemed
    redeemed, entitlement = redeem_voucher(voucher_code=reserved.display_code, company=company)
    assert redeemed.status == VoucherStatus.REDEEMED
    assert entitlement is not None


@pytest.mark.django_db
def test_invalid_state_transitions():
    user = User.objects.create_user(email='invalid_state@example.com', password='Password123!')
    company = create_company(name='Invalid Co', user=user)
    plan = create_plan(company=company, data={'name': '1H Pass', 'code': 'LAB-1H', 'price': '1000.00'})

    batch, vouchers = generate_voucher_batch(company=company, plan=plan, quantity=2, created_by=user)
    v_revoked = vouchers[0]
    v_expired = vouchers[1]

    revoke_voucher(voucher=v_revoked, company=company, revoked_by=user, reason='Testing')
    v_expired.status = VoucherStatus.EXPIRED
    v_expired.save()

    with pytest.raises(ValidationError) as exc1:
        redeem_voucher(voucher_code=v_revoked.display_code, company=company)
    assert 'revoked' in str(exc1.value).lower()

    with pytest.raises(ValidationError) as exc2:
        redeem_voucher(voucher_code=v_expired.display_code, company=company)
    assert 'expired' in str(exc2.value).lower()


from unittest.mock import patch


@pytest.mark.django_db
def test_cascading_revocation_with_entitlement_and_disconnect():
    user = User.objects.create_user(email='cascade_owner@example.com', password='Password123!')
    company = create_company(name='Cascade Co', user=user)
    plan = create_plan(company=company, data={'name': '15M Pass', 'code': 'LAB-15MIN', 'price': '500.00'})

    batch, vouchers = generate_voucher_batch(company=company, plan=plan, quantity=1, created_by=user)
    voucher = vouchers[0]

    # 1. Redeem voucher -> creates entitlement
    redeemed, entitlement = redeem_voucher(voucher_code=voucher.display_code, company=company)
    assert entitlement.status == 'ACTIVE'

    # Mock disconnect_active_sessions_for_entitlement
    with patch(
        'apps.hotspot_sessions.services.session_control.disconnect_active_sessions_for_entitlement',
        return_value=[]
    ) as mock_disconnect:
        # 2. Revoke redeemed voucher -> cascades to entitlement & disconnect
        revoked = revoke_voucher(voucher=redeemed, company=company, revoked_by=user, reason='Customer requested cancellation')
        assert revoked.status == VoucherStatus.REVOKED

        entitlement.refresh_from_db()
        assert entitlement.status == 'REVOKED'
        assert entitlement.revocation_reason == 'Customer requested cancellation'
        mock_disconnect.assert_called_once_with(
            entitlement=entitlement,
            trigger_type='ADMIN_REVOCATION',
            reason='Customer requested cancellation',
            requested_by=user
        )


@pytest.mark.django_db
def test_export_batch_routeros_script_and_csv():
    user = User.objects.create_user(email='export_owner@example.com', password='Password123!')
    company = create_company(name='Export Co', user=user)
    plan = create_plan(company=company, data={'name': '1H Pass', 'code': 'LAB-1H', 'price': '1000.00'})

    batch, vouchers = generate_voucher_batch(company=company, plan=plan, quantity=2, created_by=user)

    rsc_output = export_batch_routeros_script(batch)
    assert 'USIMAMIZI_LOCAL_FALLBACK' in rsc_output
    assert '/ip hotspot user add' in rsc_output
    assert 'profile="LAB-1H"' in rsc_output
    assert vouchers[0].display_code in rsc_output

    batch.refresh_from_db()
    assert batch.export_status == VoucherExportStatus.EXPORTED_ROUTEROS
    assert Voucher.objects.filter(batch=batch, export_status=VoucherExportStatus.EXPORTED_ROUTEROS).count() == 2

    csv_output = export_batch_csv(batch)
    assert 'code,plan_name,plan_code,batch_ref,status,distribution_state,export_status' in csv_output
    assert vouchers[0].display_code in csv_output


@pytest.mark.django_db
def test_printable_voucher_cards():
    user = User.objects.create_user(email='print_owner@example.com', password='Password123!')
    company = create_company(name='Print Co', user=user)
    plan = create_plan(company=company, data={'name': '1H Pass', 'code': 'LAB-1H', 'price': '1000.00'})

    batch, vouchers = generate_voucher_batch(company=company, plan=plan, quantity=3, created_by=user)
    cards = get_printable_voucher_cards(batch, portal_base_url='http://login.usimamizi.lab:5173')

    assert len(cards) == 3
    for c in cards:
        assert c['ssid'] == 'Usimamizi-WiFi-Lab'
        assert c['plan_name'] == '1H Pass'
        assert 'login.usimamizi.lab:5173' in c['qr_url']
        assert c['code'] in [v.display_code for v in vouchers]


@pytest.mark.django_db
def test_voucher_metrics_and_timeline():
    user = User.objects.create_user(email='metrics_owner@example.com', password='Password123!')
    company = create_company(name='Metrics Co', user=user)
    plan = create_plan(company=company, data={'name': '1H Pass', 'code': 'LAB-1H', 'price': '1000.00'})

    batch, vouchers = generate_voucher_batch(company=company, plan=plan, quantity=3, created_by=user)
    redeem_voucher(voucher_code=vouchers[0].display_code, company=company)
    revoke_voucher(voucher=vouchers[1], company=company, revoked_by=user, reason='Damaged')

    metrics = get_voucher_metrics(company)
    assert metrics['total'] == 3
    assert metrics['available'] == 1
    assert metrics['redeemed'] == 1
    assert metrics['revoked'] == 1
    assert metrics['redemption_rate'] == 33.3

    vouchers[0].refresh_from_db()
    timeline = get_voucher_timeline(vouchers[0])
    event_names = [e['event'] for e in timeline]
    assert 'VOUCHER_CREATED' in event_names
    assert 'VOUCHER_REDEEMED' in event_names


@pytest.mark.django_db
def test_voucher_tenant_isolation():
    user1 = User.objects.create_user(email='tenant1@example.com', password='Password123!')
    company1 = create_company(name='Tenant 1', user=user1)
    plan1 = create_plan(company=company1, data={'name': 'Plan 1', 'code': 'PL-1', 'price': '1000.00'})
    batch1, vouchers1 = generate_voucher_batch(company=company1, plan=plan1, quantity=1, created_by=user1)

    user2 = User.objects.create_user(email='tenant2@example.com', password='Password123!')
    company2 = create_company(name='Tenant 2', user=user2)

    # Tenant 2 attempts to redeem Tenant 1 voucher -> Failure
    with pytest.raises(ValidationError):
        redeem_voucher(voucher_code=vouchers1[0].display_code, company=company2)

    # Tenant 2 cannot revoke Tenant 1 voucher
    with pytest.raises(ValidationError):
        revoke_voucher(voucher=vouchers1[0], company=company2, revoked_by=user2)
