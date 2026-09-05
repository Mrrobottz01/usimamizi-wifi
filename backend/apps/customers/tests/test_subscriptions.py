from datetime import timedelta
from decimal import Decimal
import pytest
from django.utils import timezone

from apps.companies.models import Company
from apps.customers.models import (
    CustomerSubscriptionSettings,
    Subscription,
    SubscriptionEventType,
    SubscriptionStatus,
)
from apps.customers.services.customer_services import get_or_create_customer
from apps.customers.services.subscription_services import (
    activate_subscription,
    calculate_plan_duration,
    create_subscription,
    process_subscription_expiries,
    reactivate_subscription,
    renew_subscription,
    suspend_subscription,
)
from apps.entitlements.models import EntitlementStatus
from apps.plans.models import DurationUnit, Plan, ValidityMode


@pytest.fixture
def subscription_setup(db):
    company = Company.objects.create(name="Hotspot Hub", slug="hub")
    plan_daily = Plan.objects.create(
        company=company,
        name="Daily High Speed",
        code="DAILY-5M",
        price=Decimal("1500.00"),
        currency="TZS",
        duration_value=1,
        duration_unit=DurationUnit.DAYS,
        validity_mode=ValidityMode.CALENDAR,
        download_speed_kbps=5120,
        upload_speed_kbps=2048,
        is_active=True,
    )
    customer, _ = get_or_create_customer(company=company, phone="0712345678", first_name="Amina")
    return company, plan_daily, customer


@pytest.mark.django_db
def test_create_and_activate_subscription(subscription_setup):
    company, plan, customer = subscription_setup

    sub = create_subscription(
        customer=customer,
        plan=plan,
        hotspot=None,
        auto_activate=True,
    )
    assert sub.status == SubscriptionStatus.ACTIVE
    assert sub.started_at is not None
    assert sub.current_period_start is not None
    assert sub.current_period_end is not None
    assert sub.remaining_seconds > 0
    assert sub.is_valid_now is True

    # Entitlement verification
    ent = sub.entitlements.first()
    assert ent is not None
    assert ent.consumer == customer
    assert ent.subscription == sub
    assert ent.status == EntitlementStatus.ACTIVE
    assert ent.download_speed_kbps == 5120


@pytest.mark.django_db
def test_lossless_active_subscription_renewal(subscription_setup):
    company, plan, customer = subscription_setup

    sub = create_subscription(
        customer=customer,
        plan=plan,
        auto_activate=True,
    )
    initial_end = sub.current_period_end

    # Fast forward: customer still has 12 hours remaining
    sub.current_period_end = timezone.now() + timedelta(hours=12)
    sub.save(update_fields=['current_period_end'])
    remaining_end_before_renew = sub.current_period_end

    # Customer renews while ACTIVE
    renewed_sub, new_ent = renew_subscription(subscription=sub)

    # Expected: new_start is the exact previous period end, and new_end is +1 day after that
    assert renewed_sub.status == SubscriptionStatus.ACTIVE
    assert renewed_sub.current_period_start == remaining_end_before_renew
    expected_new_end = remaining_end_before_renew + timedelta(days=1)
    assert abs((renewed_sub.current_period_end - expected_new_end).total_seconds()) < 2
    assert new_ent.expires_at == renewed_sub.current_period_end


@pytest.mark.django_db
def test_expired_subscription_renewal(subscription_setup):
    company, plan, customer = subscription_setup

    sub = create_subscription(
        customer=customer,
        plan=plan,
        auto_activate=True,
    )
    # Mark expired
    sub.status = SubscriptionStatus.EXPIRED
    sub.current_period_end = timezone.now() - timedelta(hours=5)
    sub.save(update_fields=['status', 'current_period_end'])

    now_before = timezone.now()
    renewed_sub, new_ent = renew_subscription(subscription=sub)
    now_after = timezone.now()

    assert renewed_sub.status == SubscriptionStatus.ACTIVE
    assert now_before <= renewed_sub.current_period_start <= now_after
    assert abs((renewed_sub.current_period_end - (renewed_sub.current_period_start + timedelta(days=1))).total_seconds()) < 2


@pytest.mark.django_db
def test_suspend_and_reactivate_subscription(subscription_setup):
    company, plan, customer = subscription_setup

    sub = create_subscription(
        customer=customer,
        plan=plan,
        auto_activate=True,
    )
    ent = sub.entitlements.first()
    assert ent.status == EntitlementStatus.ACTIVE

    # Suspend
    suspended = suspend_subscription(sub, reason="Fraud check")
    assert suspended.status == SubscriptionStatus.SUSPENDED
    ent.refresh_from_db()
    assert ent.status == EntitlementStatus.REVOKED

    # Reactivate (period is still unexpired)
    reactivated, new_ent = reactivate_subscription(suspended)
    assert reactivated.status == SubscriptionStatus.ACTIVE
    assert new_ent.status == EntitlementStatus.ACTIVE


@pytest.mark.django_db
def test_process_subscription_expiries_grace_and_expire(subscription_setup):
    company, plan, customer = subscription_setup
    settings_obj, _ = CustomerSubscriptionSettings.objects.get_or_create(
        company=company,
        defaults={'grace_period_minutes': 30}
    )

    sub = create_subscription(
        customer=customer,
        plan=plan,
        auto_activate=True,
    )
    # Set period end to 5 minutes ago (within 30-min grace window)
    sub.current_period_end = timezone.now() - timedelta(minutes=5)
    sub.save(update_fields=['current_period_end'])

    stats = process_subscription_expiries()
    assert stats['grace_entered'] == 1
    sub.refresh_from_db()
    assert sub.status == SubscriptionStatus.GRACE
    assert sub.grace_period_end is not None

    # Fast forward past grace period
    sub.grace_period_end = timezone.now() - timedelta(minutes=2)
    sub.save(update_fields=['grace_period_end'])

    stats2 = process_subscription_expiries()
    assert stats2['expired'] == 1
    sub.refresh_from_db()
    assert sub.status == SubscriptionStatus.EXPIRED
