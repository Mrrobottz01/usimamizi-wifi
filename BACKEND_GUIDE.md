# BACKEND_GUIDE.md
## Wi-Fi Hotspot Management SaaS
### Backend Architecture, Domain Rules & Agent Implementation Standard

**Version:** 1.0  
**Status:** Mandatory Backend Standard  
**Applies To:** Django, Django REST Framework, PostgreSQL, Redis, Celery, FreeRADIUS integrations, MikroTik integrations, payments, SaaS billing, reporting and platform administration

---

# 1. PURPOSE

This document defines the mandatory backend engineering rules for the Wi-Fi Hotspot Management SaaS.

Every backend implementation agent must read this file before creating or modifying backend code.

The backend must be:

- secure
- multi-tenant
- transactionally correct
- auditable
- testable
- modular
- observable
- integration-safe
- operationally predictable

The backend must not become a collection of views, serializers and signal handlers containing hidden business rules.

The system manages:

- customer money
- SaaS subscription money
- internet access rights
- vouchers
- routers
- network sessions
- RADIUS authentication
- RADIUS accounting
- platform permissions

Therefore backend correctness takes priority over implementation convenience.

---

# 2. MANDATORY READING ORDER

Before implementing a backend feature, agents must read:

1. `PROJECT_ARCHITECTURE.md`
2. `BACKEND_GUIDE.md`
3. relevant domain/API specification
4. relevant database/model documentation
5. relevant frontend screen specification when API behavior affects UX

If a later approved domain specification explicitly overrides this guide for a specific feature, the explicit approved specification wins for that feature only.

---

# 3. CORE BACKEND PRINCIPLE

The SaaS database is the commercial and domain source of truth.

The router is not the source of truth for:

- customers
- payments
- plans
- entitlements
- subscriptions
- vouchers
- tenant ownership

The router is an enforcement and observation device.

Conceptually:

```text
Payment
   ↓
Backend Business Logic
   ↓
Access Entitlement
   ↓
RADIUS Authorization
   ↓
MikroTik Enforcement
   ↓
RADIUS Accounting
   ↓
Session/Usage Evidence
```

Do not architect core business state around local MikroTik HotSpot users.

---

# 4. RECOMMENDED STACK

Backend:

```text
Python
Django
Django REST Framework
PostgreSQL
Redis
Celery
Celery Beat
FreeRADIUS
```

Infrastructure may additionally include:

```text
Nginx
Gunicorn
systemd or containers
structured logging
monitoring/alerting
```

---

# 5. DJANGO APPLICATION BOUNDARIES

Recommended domain layout:

```text
backend/
└── apps/
    ├── accounts/
    ├── companies/
    ├── locations/
    ├── routers/
    ├── hotspots/
    ├── customers/
    ├── devices/
    ├── plans/
    ├── entitlements/
    ├── sessions/
    ├── vouchers/
    ├── payments/
    ├── radius/
    ├── subscriptions/
    ├── billing/
    ├── reports/
    ├── notifications/
    ├── audit/
    ├── support/
    └── platform_admin/
```

Do not create one giant `core` app containing unrelated business domains.

---

# 6. INTERNAL APP STRUCTURE

Important business apps should follow a structure similar to:

```text
apps/payments/
├── models.py
├── admin.py
├── api/
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── filters.py
├── services/
├── selectors/
├── integrations/
├── tasks.py
├── permissions.py
├── exceptions.py
├── migrations/
└── tests/
```

Not every app must contain every folder, but business logic placement must remain consistent.

---

# 7. BUSINESS LOGIC PLACEMENT

## Services

Use services for commands and state transitions.

Examples:

```text
activate_entitlement(...)
redeem_voucher(...)
confirm_payment(...)
disconnect_session(...)
provision_router(...)
suspend_company(...)
renew_subscription(...)
```

Services should:

- validate business invariants
- perform state transitions
- control transactions
- invoke integration adapters where appropriate
- create audit evidence
- return explicit results

## Selectors

Use selectors for complex reads.

Examples:

```text
get_company_dashboard(...)
list_active_sessions(...)
get_router_health(...)
get_customer_access_history(...)
```

Selectors:

- do not mutate state
- centralize tenant scoping
- optimize joins/prefetching
- prevent duplicated query logic

---

# 8. SERIALIZER RULE

Serializers are API boundary tools.

They may:

- validate input shape
- normalize fields
- serialize output
- perform simple field-level validation

They must not contain core domain workflows.

Forbidden:

```python
def create(self, validated_data):
    # payment provider call
    # create entitlement
    # configure router
    # send notification
```

Business workflows belong in services.

---

# 9. VIEW RULE

Views/ViewSets should remain thin.

Typical flow:

```text
authenticate
authorize
deserialize
call service/selector
serialize response
```

Views must not contain:

- payment reconciliation logic
- router provisioning logic
- voucher redemption logic
- subscription transitions
- entitlement expiration rules

---

# 10. SIGNAL RULE

Use Django signals sparingly.

Do not hide critical business workflows in `post_save`.

Avoid:

```text
Payment saved
→ signal creates entitlement
→ another signal touches router
→ another signal sends notification
```

This creates invisible execution paths and fragile tests.

Prefer explicit service orchestration.

Signals are acceptable for narrowly scoped non-critical decoupled behavior where failure semantics are understood.

---

# 11. TENANCY MODEL

Every tenant-owned record must ultimately belong to a company.

Examples:

```text
Plan.company
Router.company
Hotspot.company
Customer.company
Payment.company
Voucher.company
Entitlement.company
Session.company
```

A location does not replace company ownership.

Where useful, storing both:

```text
company_id
location_id
```

is acceptable for query efficiency and explicit tenancy, provided invariants guarantee consistency.

---

# 12. TENANT ISOLATION

Tenant isolation is mandatory at backend query level.

Never rely on frontend filtering.

Forbidden in tenant APIs:

```python
Payment.objects.all()
```

Preferred conceptual pattern:

```python
Payment.objects.filter(company=request.company)
```

Better still:

- tenant-scoped selectors
- tenant-aware managers/querysets
- reusable permission helpers
- tests proving cross-tenant denial

---

# 13. TENANT INVARIANT

If an object references another tenant-owned object, their companies must match.

Examples:

```text
Router.company == Router.location.company
Plan.company == Entitlement.company
Customer.company == Payment.company
Hotspot.company == Router.company
```

Validate this in services and reinforce with database design where feasible.

---

# 14. PLATFORM ADMIN BOUNDARY

Platform administrators may access multiple tenants only through explicit platform-level APIs and permissions.

Do not let ordinary tenant endpoints become “superuser-aware” in ways that accidentally bypass isolation.

Cross-tenant support access must be:

- explicit
- permissioned
- auditable

---

# 15. IDENTIFIERS

Use stable non-guessable identifiers for public APIs.

Recommended:

```text
UUID
```

Human-readable references may coexist:

```text
PAY-20260819-XXXX
VCH-BATCH-000001
RTR-000001
```

Do not use human-readable references as the only database key.

---

# 16. MONEY

Use decimal arithmetic.

Never use floating point for money.

Store:

```text
amount
currency
```

Use database decimal fields with explicit precision.

Payment amount accepted by backend must be derived from backend plan/order state, never trusted from frontend request amount.

---

# 17. TIME

Store timestamps in UTC.

Display according to tenant/user timezone.

Use timezone-aware datetimes everywhere.

Do not use naive datetimes.

---

# 18. IMMUTABLE FINANCIAL EVIDENCE

Confirmed payment records are financial evidence.

Do not silently rewrite:

- provider reference
- paid amount
- confirmation time
- original order
- historical plan snapshot where required

Corrections should occur via:

- refund
- reversal
- compensating record
- explicit administrative adjustment

not silent editing.

---

# 19. PAYMENT DOMAIN MODEL

Recommended entities:

```text
PaymentProvider
PaymentOrder
PaymentAttempt
PaymentTransaction
PaymentWebhookEvent
Refund
```

Separate the commercial order from provider attempts.

One order may have multiple failed attempts before one succeeds.

---

# 20. PAYMENT ORDER STATES

Recommended:

```text
CREATED
PENDING
PAID
FAILED
EXPIRED
CANCELLED
REFUNDED
```

All state transitions must go through services.

Do not directly set arbitrary status fields from API serializers.

---

# 21. PAYMENT CONFIRMATION RULE

Internet access is not activated because the frontend displays success.

Correct flow:

```text
Provider callback/webhook
        ↓
Verify authenticity
        ↓
Persist webhook event
        ↓
Resolve transaction/order
        ↓
Idempotently mark payment confirmed
        ↓
Create/activate entitlement
        ↓
RADIUS authorizes access
```

---

# 22. PAYMENT WEBHOOKS

Webhook handling must support:

- signature/auth verification
- raw event retention where appropriate
- idempotency
- replay safety
- duplicate delivery
- delayed delivery
- out-of-order delivery
- unknown references
- provider retries

Never assume provider sends one webhook exactly once.

---

# 23. WEBHOOK IDEMPOTENCY

Provider callback repeated five times must produce:

```text
1 payment confirmation
1 entitlement activation
```

not five entitlements.

Use:

- unique provider event/reference constraints
- transaction locking
- idempotent services

---

# 24. PAYMENT ADAPTERS

Provider-specific code belongs in adapters.

Conceptual interface:

```text
initiate_payment(...)
query_payment(...)
verify_webhook(...)
refund(...)
```

Business services must not contain scattered provider-specific request payloads.

Directory:

```text
payments/integrations/
├── base.py
├── mpesa.py
├── airtel_money.py
├── mixx.py
└── ...
```

---

# 25. SAAS BILLING SEPARATION

Keep hotspot customer payments separate from SaaS subscription payments.

Hotspot flow:

```text
End Customer → Hotspot Operator
```

SaaS flow:

```text
Hotspot Operator → Platform
```

Separate models and reports.

Never mix these ledgers.

---

# 26. ENTITLEMENT MODEL

An internet purchase/grant creates an entitlement.

Suggested fields include:

```text
company
customer
plan
payment/order/voucher source
status
starts_at
expires_at
allowed_seconds
used_seconds
allowed_data
used_data
max_devices
activation_source
```

The entitlement is the authorization right.

It is not the same as a network session.

---

# 27. ENTITLEMENT STATES

Recommended:

```text
PENDING
ACTIVE
EXHAUSTED
EXPIRED
REVOKED
SUSPENDED
```

Transitions must go through services.

---

# 28. ENTITLEMENT ACTIVATION

Activation service must validate:

- tenant
- plan
- order/payment source
- customer
- start policy
- expiry policy
- device limits
- duplicate activation

Creation and activation may be combined or separate depending domain needs, but semantics must remain explicit.

---

# 29. SESSION MODEL

A network session is usage evidence.

Recommended fields:

```text
company
hotspot
router
customer
device
entitlement
radius_session_id
ip_address
mac_address
started_at
last_accounting_at
ended_at
input_bytes
output_bytes
session_seconds
termination_reason
status
```

---

# 30. SESSION STATES

Recommended:

```text
AUTHENTICATING
ACTIVE
DISCONNECTED
EXPIRED
TERMINATED
STALE
```

Do not equate “no stop packet yet” with “definitely active.”

---

# 31. RADIUS ROLE

FreeRADIUS is the AAA layer.

Responsibilities:

- authentication
- authorization
- session controls
- accounting intake

Django remains the business/domain source of truth.

Do not duplicate commercial logic into opaque RADIUS configuration where Django can own it clearly.

---

# 32. RADIUS AUTHORIZATION

Authorization decision should derive from:

- customer/device identity
- active entitlement
- expiry
- allowed usage
- device/session limits
- tenant/hotspot context
- suspension/block state

RADIUS should not authorize expired or revoked entitlements.

---

# 33. RADIUS ACCOUNTING

Support:

- accounting start
- interim updates
- accounting stop

Accounting processing must tolerate:

- duplicate packets
- delayed packets
- out-of-order packets
- missing stop packets
- router restart
- stale sessions

Use idempotent updates keyed by RADIUS/session identifiers.

---

# 34. USAGE ACCOUNTING

Usage totals must not decrease due to out-of-order updates.

If interim updates provide cumulative byte counters, persist monotonic progress safely.

Never double-count cumulative values as deltas.

Tests must cover router counter behavior.

---

# 35. STALE SESSIONS

Background reconciliation should identify sessions where:

```text
last_accounting_at
```

has exceeded a configured threshold.

Mark as `STALE` only through controlled reconciliation logic.

Do not delete stale sessions.

Historical usage evidence must remain.

---

# 36. ROUTER DOMAIN

Router model stores identity and management metadata.

Suggested:

```text
company
location
name
serial_number
identity
model
architecture
routeros_version
connection_type
connection_status
last_seen_at
last_sync_at
provisioning_status
encrypted_credentials
```

---

# 37. ROUTER ADAPTER ABSTRACTION

All MikroTik operations must go through an adapter interface.

Conceptual interface:

```text
connect()
health()
get_resource_info()
get_active_sessions()
disconnect_session()
sync_radius()
provision_hotspot()
sync_profile()
backup_configuration()
```

Implementations may include:

```text
MikrotikLegacyApiAdapter
MikrotikRestAdapter
```

Do not scatter RouterOS commands throughout services.

---

# 38. ROUTER VERSION CAPABILITIES

Backend must detect and persist router capabilities.

Do not assume every MikroTik supports the same management API.

Use capability checks such as:

```text
supports_rest
supports_wireguard
supports_required_hotspot_features
```

Prefer feature detection/capability policy over hardcoded UI guesses.

---

# 39. ROUTER CREDENTIALS

Never expose router credentials through normal serializers.

Requirements:

- encrypted at rest
- masked in administration UI
- redacted from logs
- accessible only to integration service boundary

Plaintext credentials must not be stored in logs, Celery task arguments or audit metadata.

---

# 40. ROUTER CONNECTION STATUS

Recommended states:

```text
UNREGISTERED
REGISTERED
PROVISIONING
ONLINE
DEGRADED
OFFLINE
FAILED
```

Status changes should be derived from health rules, not one transient failed request.

Use consecutive-failure/recovery thresholds.

---

# 41. ROUTER HEARTBEATS

Persist:

```text
last_seen_at
last_health_at
last_successful_connection_at
```

The frontend must be able to distinguish:

- online
- recently seen
- stale
- offline

Backend should expose this explicitly.

---

# 42. ROUTER PROVISIONING

Provisioning must be controlled and idempotent.

Conceptual sequence:

```text
validate router
detect version/capabilities
backup
configure management
configure hotspot
configure RADIUS
configure portal/walled garden
run verification
mark ready
```

Running provisioning twice must not create duplicate rules/configuration.

---

# 43. DESIRED VS OBSERVED CONFIGURATION

Long-term router management should distinguish:

```text
desired state
observed state
```

Example:

```text
desired RADIUS server = X
observed RADIUS server = missing
```

Then mark configuration:

```text
IN_SYNC
DRIFTED
UNKNOWN
```

Do not silently overwrite router configuration without audit.

---

# 44. VOUCHERS

Voucher domain must support:

- batches
- single-use codes
- expiry
- redemption
- revocation
- plan association

Voucher redemption is concurrency-sensitive.

---

# 45. VOUCHER CODE SECURITY

Do not store only easily guessable sequential codes.

Codes must have sufficient entropy.

Where appropriate store:

```text
display_code
code_hash
```

rather than relying on plaintext search for all operations.

Rate-limit redemption attempts.

---

# 46. VOUCHER REDEMPTION

Redemption must be atomic.

Conceptual:

```text
lock voucher
validate AVAILABLE
validate expiry
validate tenant/hotspot
mark redeemed
create entitlement
commit
```

Two concurrent redemption requests must not both succeed.

---

# 47. DEVICES

Device records may use MAC address operationally.

Do not treat MAC as immutable human identity.

Modern devices may randomize MAC addresses.

Business logic should associate:

```text
customer
device
entitlement
```

without assuming one MAC permanently identifies one customer.

---

# 48. DEVICE BLOCKING

Blocking must be explicit and audited.

Suggested:

```text
is_blocked
blocked_reason
blocked_by
blocked_at
```

Authorization logic must enforce blocked state.

---

# 49. PLANS

Plan model must support:

- price
- duration
- validity mode
- speed
- data limit
- device limit
- simultaneous sessions
- activation rules

Plan changes must not rewrite historical payment evidence.

Where required, snapshot commercial plan terms onto order/entitlement records.

---

# 50. PLAN VALIDITY MODES

Support explicit modes such as:

```text
CONTINUOUS
USAGE_TIME
CALENDAR
```

Do not implement validity using ambiguous generic integer fields without mode semantics.

---

# 51. SUBSCRIPTIONS

SaaS subscription state must be explicit.

Suggested:

```text
TRIAL
ACTIVE
PAST_DUE
SUSPENDED
CANCELLED
EXPIRED
```

Subscription enforcement policy must be centralized.

Do not scatter:

```python
if company.subscription_status != ...
```

through random views.

---

# 52. PERMISSIONS

Use explicit RBAC.

Concepts:

```text
Role
Permission
UserRole
UserLocationAccess
```

Example permissions:

```text
routers.view
routers.configure
routers.disconnect_session
payments.view
payments.refund
vouchers.generate
vouchers.revoke
plans.create
reports.financial
staff.manage
```

---

# 53. OBJECT-LEVEL ACCESS

Location-scoped roles must only access assigned locations.

Permission evaluation should consider:

- user
- company
- role
- permission
- location scope
- object

Do not implement authorization only at menu level.

---

# 54. AUDIT LOGGING

Sensitive actions must create immutable audit evidence.

Examples:

- router configured
- payment overridden
- refund issued
- voucher revoked
- manual access granted
- device blocked
- company suspended
- user role changed
- subscription changed

Suggested fields:

```text
actor
company
action
object_type
object_id
before
after
ip_address
request_id
created_at
```

---

# 55. AUDIT SAFETY

Do not log secrets.

Redact:

- passwords
- API keys
- provider secrets
- router credentials
- tokens

Audit logs are not an excuse to copy entire sensitive payloads.

---

# 56. BACKGROUND TASKS

Use Celery for work that should not block HTTP requests.

Examples:

- router health checks
- report generation
- notifications
- reconciliation
- webhook follow-up
- subscription renewal processing
- stale session reconciliation

Do not move transactional correctness into background tasks merely for convenience.

---

# 57. TASK IDEMPOTENCY

Celery tasks may retry.

Therefore tasks must be safe under retry.

Do not assume:

```text
task executes exactly once
```

Design:

```text
at-least-once execution
+
idempotent operation
```

---

# 58. TASK ARGUMENTS

Pass stable identifiers, not large model snapshots.

Good:

```text
router_id
payment_id
company_id
```

Bad:

```text
full credentials
large serialized objects
secret payloads
```

---

# 59. TRANSACTIONS

Use `transaction.atomic()` for state transitions involving multiple writes.

Examples:

- payment confirmation + entitlement activation
- voucher redemption + entitlement creation
- subscription renewal
- manual access grant
- refund state transitions

---

# 60. ROW LOCKING

Use `select_for_update()` where concurrent modification could violate invariants.

Examples:

- voucher redemption
- payment confirmation
- subscription renewal
- unique sequential reference generation if used
- entitlement exhaustion transitions

---

# 61. DATABASE CONSTRAINTS

Business invariants should be reinforced at database level where possible.

Examples:

- unique provider reference
- unique webhook event identifier
- unique voucher code per company
- unique router serial per company where applicable
- non-negative monetary values
- valid quantities
- unique active constraints where domain requires

Application validation alone is not sufficient for concurrency.

---

# 62. REFERENCE NUMBER GENERATION

Human references must be concurrency-safe.

Do not use:

```python
count() + 1
```

as reference generation.

Use:

- sequence model with locking
- database sequence
- UUID-based reference
- another concurrency-safe method

---

# 63. SOFT DELETE VS HARD DELETE

Financial and operational evidence should rarely be hard-deleted.

Never hard-delete confirmed:

- payments
- refunds
- accounting sessions
- audit events
- redeemed vouchers

Use status transitions or archival policies.

Draft/configuration objects may be deletable if domain rules allow.

---

# 64. API VERSIONING

Use:

```text
/api/v1/
```

Keep portal endpoints logically separate:

```text
/api/v1/portal/
```

Keep webhook endpoints explicit:

```text
/api/v1/webhooks/
```

Do not expose internal integration endpoints as ordinary tenant API.

---

# 65. API RESPONSE CONSISTENCY

Use consistent pagination, errors and metadata.

Define one error structure.

Example conceptual shape:

```json
{
  "code": "PAYMENT_ALREADY_CONFIRMED",
  "detail": "This payment has already been confirmed.",
  "field_errors": {}
}
```

Do not return random error shapes from each app.

---

# 66. DOMAIN EXCEPTIONS

Create explicit domain exceptions.

Examples:

```text
VoucherAlreadyRedeemed
PaymentAlreadyConfirmed
EntitlementExpired
RouterUnavailable
TenantMismatch
SubscriptionSuspended
DeviceLimitReached
```

Map them consistently to API responses.

---

# 67. HTTP STATUS CODES

Use meaningful HTTP semantics.

Typical:

```text
200 OK
201 Created
204 No Content
400 Bad Request
401 Unauthorized
403 Forbidden
404 Not Found
409 Conflict
422 Unprocessable Entity where project convention allows
429 Too Many Requests
503 Service Unavailable
```

Do not return `200` with `"success": false` for every failure.

---

# 68. FILTERING

Use explicit backend filtering for lists.

Examples:

- date range
- location
- router
- plan
- payment status
- provider
- customer
- session status

Never fetch massive datasets and filter in frontend.

---

# 69. PAGINATION

All potentially large list endpoints require pagination.

Examples:

- customers
- payments
- sessions
- vouchers
- audit logs
- routers at platform scale

---

# 70. QUERY PERFORMANCE

Avoid N+1 queries.

Use:

- `select_related`
- `prefetch_related`
- annotations
- indexes
- query profiling

Selectors should own complex optimized reads.

---

# 71. DATABASE INDEXING

Index frequently queried fields such as:

- company
- location
- status
- created_at
- provider reference
- payment reference
- phone number
- router status
- last_seen_at
- session identifiers

Composite indexes should follow real query patterns.

---

# 72. PHONE NUMBERS

Normalize phone numbers before persistence.

Recommended canonical representation:

```text
+255712345678
```

Display formatting belongs to frontend/presentation layer.

Use centralized normalization/validation.

---

# 73. API INPUT TRUST

Never trust frontend for:

- plan price
- company ownership
- payment status
- router identity
- entitlement expiry
- role authorization
- voucher status

Resolve these on backend.

---

# 74. FILES AND EXPORTS

Generated reports should come from backend data.

Exports may include:

- CSV
- Excel
- PDF

Large report generation should use asynchronous jobs where appropriate.

Generated files must be scoped to the requesting tenant.

---

# 75. REPORTING

Financial reports should derive from immutable transactional evidence.

Network reports should derive from session/accounting evidence.

Do not compute critical financial totals from frontend caches.

---

# 76. NOTIFICATIONS

Notifications are downstream effects.

A failed notification must not roll back a successfully confirmed payment.

Use:

```text
transaction commit
→ enqueue notification
```

where appropriate.

---

# 77. ON_COMMIT

When enqueueing background work dependent on committed database state, use transaction commit hooks where appropriate.

Avoid workers reading records that the request transaction has not committed yet.

---

# 78. RETRIES

Retries must be explicit by integration type.

Safe retry candidates:

- transient router API timeout
- temporary payment status query
- notification provider outage

Unsafe blind retry:

- non-idempotent financial mutation
- destructive router reset
- duplicate refund call

Adapters/services must define retry behavior.

---

# 79. EXTERNAL REQUEST TIMEOUTS

Every external network call must have a timeout.

Never allow:

```text
requests.get(...)
```

with unlimited blocking in production.

Define:

- connection timeout
- read timeout
- retry policy
- failure mapping

---

# 80. CIRCUIT/DEGRADATION THINKING

One broken external provider should not crash unrelated APIs.

Examples:

- payment provider down
- router offline
- WhatsApp unavailable

Return controlled domain errors and preserve unrelated platform functionality.

---

# 81. SECURITY BASELINE

Backend must enforce:

- HTTPS
- secure auth
- strong password hashing
- token/session security
- RBAC
- tenant isolation
- rate limiting
- webhook verification
- secret management
- audit logging
- CSRF protection where relevant
- secure CORS configuration
- input validation
- dependency updates
- database backups

---

# 82. AUTHENTICATION

Authentication mechanism must be centralized.

Avoid custom auth logic per app.

Access tokens/session behavior should be documented clearly.

Sensitive account changes may require re-authentication depending policy.

---

# 83. RATE LIMITING

Apply rate limits particularly to:

- login
- password reset
- portal payment initiation
- voucher redemption
- webhook endpoints where appropriate
- public status polling
- support/contact forms

Voucher brute force must be explicitly addressed.

---

# 84. CORS

Do not use unrestricted production CORS.

Allow only approved frontend origins.

Captive portal/public API origin needs should be deliberate.

---

# 85. SECRET MANAGEMENT

Secrets include:

- Django secret
- DB password
- Redis credentials
- payment API credentials
- webhook secrets
- router credentials
- RADIUS secrets

Do not commit secrets to repository.

Use environment/config secret storage.

---

# 86. LOGGING

Use structured logging.

Include where relevant:

```text
request_id
company_id
user_id
router_id
payment_reference
radius_session_id
task_id
```

Never log sensitive secrets.

---

# 87. OBSERVABILITY

Monitor:

- API errors
- API latency
- database health
- Redis
- Celery queue
- Celery failures
- FreeRADIUS
- payment webhook latency
- payment failure rate
- router connectivity
- background reconciliation
- backup status

---

# 88. HEALTH ENDPOINTS

Provide health endpoints suitable for operations.

Separate:

- liveness
- readiness
- dependency health

Do not make a public health endpoint expose secrets or internal infrastructure detail.

---

# 89. BACKUPS

Back up:

- PostgreSQL
- application configuration
- RADIUS configuration
- router configuration where policy requires

A backup strategy is incomplete until restore is tested.

---

# 90. MIGRATIONS

All model changes require Django migrations.

Migration rules:

- deterministic
- production-safe
- reviewed
- reversible where reasonable
- tested against realistic data

Do not manually change production schema without migration tracking.

---

# 91. DATA MIGRATIONS

Data migrations must:

- be idempotent where feasible
- operate in bounded batches for large datasets
- avoid unsafe assumptions
- log/document transformation rules

Never fabricate missing financial evidence during migration.

---

# 92. DESTRUCTIVE MIGRATIONS

For:

- dropping columns
- changing semantics
- replacing identifiers

use staged migrations.

Typical:

```text
add new field
backfill
deploy dual-read/write where needed
verify
remove old field later
```

Do not casually drop production evidence in one migration.

---

# 93. TESTING LAYERS

Required:

## Unit tests

Pure business rules/helpers.

## Service tests

State transitions and transactions.

## API tests

Permissions, validation, response contracts.

## Integration tests

- payment provider adapter
- RADIUS
- MikroTik adapter

## End-to-end tests

Critical business flows.

---

# 94. TENANT ISOLATION TESTS

Every tenant-owned API/domain must include tests proving:

```text
Tenant A cannot read Tenant B
Tenant A cannot mutate Tenant B
Tenant A cannot reference Tenant B objects
```

This is mandatory, not optional “security hardening later.”

---

# 95. PAYMENT TESTS

Must cover:

- successful payment
- failed payment
- duplicate webhook
- unknown webhook
- delayed webhook
- duplicate confirmation race
- amount mismatch
- refunded payment
- payment provider timeout
- forged webhook rejection

---

# 96. VOUCHER TESTS

Must cover:

- valid redemption
- duplicate redemption
- concurrent redemption
- expired voucher
- revoked voucher
- wrong tenant
- brute-force/rate-limit behavior where testable

---

# 97. ENTITLEMENT TESTS

Must cover:

- activation
- expiry
- usage exhaustion
- revocation
- suspension
- duplicate activation
- device/session limit enforcement

---

# 98. RADIUS TESTS

Must cover:

- valid Access-Accept
- invalid Access-Reject
- expired entitlement
- blocked device
- accounting start
- duplicate interim
- out-of-order interim
- stop
- stale session

---

# 99. ROUTER INTEGRATION TESTS

Must cover:

- supported router
- unsupported capability
- authentication failure
- timeout
- offline router
- provisioning repeat/idempotency
- disconnect session
- configuration drift

Use mocks/fakes for most automated tests plus controlled integration environment for real MikroTik validation.

---

# 100. SUBSCRIPTION TESTS

Cover:

- trial
- active
- renewal
- past due
- suspended
- cancelled
- plan limits
- tenant behavior under suspension

---

# 101. PERMISSION TESTS

Every privileged action must test:

- allowed role
- denied role
- wrong company
- wrong location scope
- unauthenticated

---

# 102. ADMIN

Django admin is operational tooling, not the product frontend.

Admin may be used for:

- support
- controlled diagnostics
- internal operations

Do not rely on Django admin as the only implementation of core business workflows.

Apply permission and tenant safety even in admin where necessary.

---

# 103. MODEL `save()` RULE

Avoid putting complex multi-model workflows inside `save()`.

Model methods may enforce narrow model-level behavior, but cross-domain transitions belong in services.

---

# 104. FAT MODEL VS FAT SERVICE

Models should represent domain state and local invariants.

Services coordinate workflows.

Do not move every line into “service” merely to create procedural god-functions.

Keep boundaries meaningful.

---

# 105. REPOSITORY QUALITY

Code must pass:

- formatter
- linting
- type checks where configured
- unit/integration tests
- migration check
- security/static checks where configured

No feature is complete with failing tests hidden behind “temporary” skips.

---

# 106. COMMENTS

Comments should explain:

- why
- invariants
- unusual provider behavior
- protocol quirks
- concurrency reasons

Do not comment obvious syntax.

Bad:

```python
# get payment
payment = Payment.objects.get(...)
```

Good:

```python
# Lock the payment because provider callbacks may arrive concurrently.
```

---

# 107. TODO RULE

Do not leave vague production TODOs.

Bad:

```text
TODO fix security later
```

If deferred:

- document issue
- define scope
- create tracked task
- fail safely in current implementation

---

# 108. ERROR HANDLING

Catch only exceptions you can meaningfully handle.

Do not use:

```python
except Exception:
    pass
```

Do not silently swallow router/payment failures.

Translate infrastructure errors into explicit domain/application errors.

---

# 109. FAIL-CLOSED RULES

For access/security-sensitive decisions, fail closed where appropriate.

Examples:

- cannot verify payment → do not activate paid entitlement
- cannot determine tenant ownership → deny
- invalid webhook signature → reject
- expired entitlement → reject access

Do not “assume success” because the external system is inconvenient.

---

# 110. ROUTER OFFLINE BEHAVIOR

Router offline must not:

- alter historical payments
- delete entitlements
- fabricate sessions

Record connectivity problem separately.

Network state and financial state are separate concerns.

---

# 111. PAYMENT PROVIDER OFFLINE BEHAVIOR

If provider unavailable:

- payment initiation returns controlled failure/pending semantics
- no entitlement created until confirmed
- existing active users remain governed by current entitlement state

Do not invent success to improve UX.

---

# 112. DOMAIN EVENT PATTERN

The system may emit internal domain events such as:

```text
payment.completed
entitlement.activated
entitlement.expired
session.started
session.ended
router.online
router.offline
voucher.redeemed
subscription.suspended
```

Use events to decouple notifications/analytics where useful.

Do not use events to hide core transaction ordering.

---

# 113. EVENT OUTBOX

For highly reliable external event delivery, consider an outbox pattern later.

Critical transaction:

```text
DB state change
+
outbox event
```

in one transaction.

A worker publishes/processes the outbox afterward.

This is preferable to hoping a process does not crash between commit and message publish.

---

# 114. PORTAL API RULES

Public portal endpoints are a separate security boundary.

They must:

- derive tenant/hotspot context server-side
- expose only necessary data
- rate limit abuse
- validate plan availability
- calculate price server-side
- prevent voucher enumeration
- never expose tenant admin data

---

# 115. PORTAL PAYMENT RULE

Frontend may submit:

```text
hotspot
plan_id
phone
provider
```

Backend determines:

```text
company
actual plan
actual price
currency
availability
order reference
```

Never accept arbitrary amount from browser as authoritative.

---

# 116. SUPPORT ACCESS

Platform support personnel accessing tenant data must use explicit support permissions.

Where possible record:

```text
support actor
tenant
reason/context
timestamp
```

Cross-tenant support should never be invisible.

---

# 117. PRIVACY

Collect only data needed for:

- providing internet access
- payment
- fraud/security controls
- operational reporting
- legal/business requirements

Avoid unnecessary invasive fingerprinting.

Define retention policies for:

- sessions
- device identifiers
- payment evidence
- logs
- audit records

---

# 118. DATA RETENTION

Do not delete evidence merely because UI no longer displays it.

Retention policy must distinguish:

- financial evidence
- audit evidence
- operational logs
- network accounting
- transient technical logs

---

# 119. SOFT SUSPENSION

When company subscription is suspended, apply a defined policy.

Possible policy decisions belong in architecture/product rules.

Do not automatically destroy:

- company data
- payments
- vouchers
- session history
- configuration

Suspension is a state, not deletion.

---

# 120. FEATURE IMPLEMENTATION CHECKLIST

Before coding a backend feature, identify:

1. domain owner/app
2. tenant scope
3. models
4. invariants
5. permissions
6. service commands
7. selectors
8. API endpoints
9. external integrations
10. transaction boundaries
11. idempotency needs
12. concurrency risks
13. audit requirements
14. background tasks
15. tests
16. migration impact
17. observability/logging

Do not begin with a serializer and “figure out the architecture later.”

---

# 121. DEFINITION OF DONE

A backend feature is complete only when:

- domain rules are implemented
- tenant isolation is enforced
- permissions are enforced
- services/selectors are used correctly
- database constraints exist where appropriate
- transactions are safe
- idempotency is addressed
- external failures are handled
- audit requirements are covered
- tests pass
- migrations are present
- API behavior is documented
- secrets are not exposed
- logging/observability are adequate
- frontend contract can rely on the API

---

# 122. AGENT PROHIBITIONS

Backend agents must NOT:

- place major business logic in serializers
- place workflows in views
- use signals for hidden critical transactions
- trust frontend prices/statuses
- bypass tenant scoping
- hardcode tenant IDs
- store money as float
- create references using `count() + 1`
- expose router credentials
- expose payment secrets
- silently swallow integration failures
- assume webhook exactly-once delivery
- assume Celery exactly-once execution
- hard-delete financial evidence
- modify confirmed payments in place
- invent missing provider data
- use direct RouterOS commands outside adapters
- make migrations without tests/review
- introduce mock/fake production data
- disable permission checks to “finish the feature”

---

# 123. FINAL ENGINEERING RULE

When choosing between:

```text
shorter implementation
```

and:

```text
explicit state
clear ownership
transaction safety
tenant isolation
auditability
idempotency
```

choose the second.

The platform will eventually manage many businesses, routers, payments and customer sessions.

Architecture that feels slightly strict at one router will feel merciful at one thousand routers.

---

# END OF BACKEND_GUIDE.md
