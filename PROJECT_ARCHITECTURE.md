# PROJECT_ARCHITECTURE.md
## Wi-Fi Hotspot Management SaaS
### Master Product, System & Technical Architecture
###system name: usimamizi wifi

**Version:** 1.0  
**Status:** Authoritative Architecture Baseline  
**Date:** August 2026

---

# 1. DOCUMENT AUTHORITY

This document is the top-level architectural source of truth for the Wi-Fi Hotspot Management SaaS.

All implementation work must conform to this document unless a later approved architecture revision explicitly changes it.

Mandatory dependent documents include:

- `BACKEND_GUIDE.md`
- `FRONTEND_GUIDE.md`
- `UI_DESIGN_SYSTEM.md`
- `WEB_SCREEN_SPECIFICATIONS.md`
- `CAPTIVE_PORTAL_SPECIFICATIONS.md`
- relevant API/domain documentation
- phase implementation plans

When lower-level documents conflict with this document, this document takes precedence unless the lower-level document contains an explicitly approved architecture override.

---

# 2. PRODUCT DEFINITION

The product is a multi-tenant SaaS platform for operating, selling, controlling and monitoring Wi-Fi hotspot access.

It allows businesses to:

- register locations
- manage MikroTik routers
- configure hotspots
- create internet packages
- sell access
- accept mobile-money payments
- generate vouchers
- manage customers/devices
- monitor sessions
- view network health
- generate operational and financial reports
- manage staff and permissions

The platform owner can:

- onboard tenant companies
- manage SaaS subscriptions
- monitor the router fleet
- operate support
- manage platform billing
- inspect system health
- administer integrations
- review audits

---

# 3. TARGET CUSTOMERS

Primary commercial segments include:

- hotels
- lodges
- restaurants
- cafés
- bars
- apartments
- hostels
- campuses
- schools
- hospitals
- malls
- bus terminals
- offices
- events
- public Wi-Fi operators
- small Wi-Fi businesses
- small ISPs

The architecture must support both:

```text
1 location / 1 router
```

and future deployments such as:

```text
many companies
many locations
hundreds or thousands of routers
large customer/session volumes
```

---

# 4. CORE BUSINESS CONCEPT

The product is not merely a Wi-Fi login page.

It is:

> **A Hotspot Business Management Platform**

with three primary concerns:

```text
Network Access
+
Commerce
+
Operations
```

The system must keep these concerns separated internally while presenting them as one coherent product.

---

# 5. ARCHITECTURAL PRINCIPLE

The SaaS platform owns business state.

MikroTik owns network enforcement.

FreeRADIUS provides centralized AAA.

Payment providers confirm money movement.

The system follows:

```text
Payment / Voucher / Manual Grant
              ↓
       Access Entitlement
              ↓
      RADIUS Authorization
              ↓
       MikroTik Enforcement
              ↓
       RADIUS Accounting
              ↓
     Session / Usage Evidence
```

This lifecycle is foundational.

Do not replace it with:

```text
payment
→ create local MikroTik user
```

as the platform architecture.

---

# 6. SOURCES OF TRUTH

## 6.1 SaaS PostgreSQL

Authoritative for:

- companies
- locations
- staff
- roles
- routers registered to platform
- hotspot configuration intent
- customers
- plans
- orders
- payments
- vouchers
- entitlements
- SaaS subscriptions
- audit logs

## 6.2 FreeRADIUS / AAA integration

Authoritative for network authentication/authorization decisions at connection time based on SaaS entitlement state.

## 6.3 MikroTik

Authoritative for immediate observed network state such as:

- active sessions
- router resource state
- configured network state
- interface/router observations

MikroTik is not authoritative for commercial customer state.

## 6.4 Payment Providers

Authoritative external evidence for provider-side payment confirmation.

The SaaS stores normalized payment evidence and state.

---

# 7. HIGH-LEVEL SYSTEM ARCHITECTURE

```text
                          ┌────────────────────────────┐
                          │      PLATFORM OWNER        │
                          │                            │
                          │ Super Admin                │
                          │ SaaS Billing               │
                          │ Support                    │
                          └────────────┬───────────────┘
                                       │
                                       ▼
                         ┌────────────────────────────┐
                         │       WEB APPLICATION      │
                         │ React + TypeScript         │
                         └────────────┬───────────────┘
                                       │ HTTPS
                                       ▼
                    ┌────────────────────────────────────┐
                    │            SAAS BACKEND            │
                    │                                    │
                    │ Django + DRF                       │
                    │ PostgreSQL                         │
                    │ Redis                              │
                    │ Celery                             │
                    └───────┬─────────────┬──────────────┘
                            │             │
                 ┌──────────▼───┐   ┌────▼─────────────┐
                 │ FreeRADIUS   │   │ Payment Providers│
                 │ AAA          │   │ M-Pesa / Airtel  │
                 └──────┬───────┘   │ Mixx / others   │
                        │           └──────────────────┘
                        │
                  Secure Network
                        │
               ┌────────▼────────┐
               │    MikroTik     │
               │                 │
               │ HotSpot         │
               │ DHCP            │
               │ Firewall        │
               │ QoS/Bandwidth   │
               └────────┬────────┘
                        │
                        ▼
                 Wi-Fi End User
                        │
                        ▼
               Captive Portal
```

---

# 8. PRIMARY SYSTEM COMPONENTS

The production system contains the following logical components:

1. Tenant SaaS web application
2. Platform Super Admin application
3. Captive Portal
4. Django/DRF backend
5. PostgreSQL database
6. Redis
7. Celery workers
8. Celery Beat/scheduler
9. FreeRADIUS
10. MikroTik router integration layer
11. payment-provider integration layer
12. notifications layer
13. monitoring/logging infrastructure
14. backup infrastructure

---

# 9. FRONTEND SURFACES

## 9.1 Tenant SaaS

Used by:

- company owners
- administrators
- managers
- operators
- technicians

Core modules:

- dashboard
- locations
- routers
- hotspots
- sessions
- customers
- devices
- plans
- payments
- vouchers
- reports
- team
- settings

## 9.2 Platform Admin

Used by SaaS operator.

Core modules:

- platform overview
- companies
- subscriptions
- router fleet
- platform payments/billing
- system health
- support
- audit logs
- platform settings

## 9.3 Captive Portal

Used by Wi-Fi customers.

Core flow:

```text
Connect
→ Choose Plan
→ Enter Phone
→ Pay / Voucher
→ Activate
→ Browse
```

---

# 10. BACKEND DOMAIN APPS

Recommended Django domains:

```text
apps/
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

Each domain must own its business rules.

Do not create cross-domain spaghetti through serializers, views or signals.

---

# 11. MULTI-TENANCY

The SaaS is multi-company from the beginning.

Hierarchy:

```text
Platform
│
├── Company
│   ├── Location
│   │   ├── Router
│   │   ├── Hotspot
│   │   └── SSID
│   └── Location
│
└── Company
```

Every tenant-owned record must ultimately belong to a company.

Examples:

```text
Router.company
Plan.company
Customer.company
Payment.company
Voucher.company
Session.company
Entitlement.company
```

---

# 12. TENANT ISOLATION

Tenant isolation is enforced in backend queries and permissions.

Company A must never access:

- Company B customers
- Company B routers
- Company B payments
- Company B sessions
- Company B vouchers
- Company B reports

Frontend filtering is not a security boundary.

Cross-tenant access exists only in explicitly authorized platform-admin/support paths.

---

# 13. LOCATION MODEL

A Location represents a physical business site.

Examples:

- hotel
- café
- apartment block
- restaurant
- campus
- branch

A company may own multiple locations.

Location-specific access controls must be supported for staff.

---

# 14. ROUTER MODEL

A Router represents a managed MikroTik device.

Router fields conceptually include:

```text
company
location
name
identity
serial number
model
architecture
RouterOS version
connection type
management address
VPN address
connection status
provisioning status
last seen
last sync
encrypted credentials
```

Router credentials are sensitive secrets.

They must not appear in ordinary API responses.

---

# 15. ROUTER STATES

Recommended lifecycle:

```text
UNREGISTERED
     ↓
REGISTERED
     ↓
PROVISIONING
     ↓
ONLINE
```

Operational deviations:

```text
ONLINE → DEGRADED
ONLINE → OFFLINE
PROVISIONING → FAILED
```

A router state is operational evidence, not financial state.

---

# 16. ROUTER INTEGRATION STRATEGY

All MikroTik operations go through an abstraction layer.

Concept:

```text
RouterAdapter
```

Possible implementations:

```text
MikrotikLegacyApiAdapter
MikrotikRestAdapter
```

This allows support for:

- RouterOS 6 through legacy API
- RouterOS 7 through REST and/or legacy API

Business services must never directly issue arbitrary RouterOS commands.

---

# 17. CURRENT DEVELOPMENT ROUTER

Initial lab device:

```text
MikroTik hAP ac lite
Architecture: mipsbe
RouterOS: 6.49.19
```

This device is used for:

- hotspot setup
- captive portal validation
- RADIUS testing
- legacy API integration

It does not define the entire future platform capability.

---

# 18. ROUTER CONNECTIVITY

Do not assume customer routers have public IPs.

Routers may be behind:

- CGNAT
- mobile network routers
- Airtel
- Vodacom
- Yas
- Starlink
- dynamic IP
- upstream NAT

Therefore cloud-to-router connectivity must support secure tunnel/agent architecture.

Preferred modern target:

```text
Cloud
  │
Secure VPN
  │
Router
```

For suitable RouterOS 7 devices, WireGuard is preferred.

Legacy routers require compatibility strategy.

---

# 19. HOTSPOT MODEL

Router and Hotspot are separate concepts.

One router may eventually support:

- multiple hotspots
- multiple SSIDs
- separate VLANs
- separate captive portal experiences

Hotspot fields conceptually include:

```text
company
location
router
name
code
interface
address pool
DNS name
portal theme
status
```

---

# 20. CUSTOMER MODEL

Customer represents the human/entity purchasing or receiving access.

Initial onboarding should be phone-first.

Fields may include:

```text
company
phone
email optional
first name optional
last name optional
status
first seen
last seen
```

Do not require full user registration to purchase Wi-Fi.

---

# 21. DEVICE MODEL

Device stores operational identity.

Fields may include:

```text
company
customer optional
MAC
device name optional
device type optional
first seen
last seen
blocked state
```

MAC address is not permanent human identity.

Modern devices may randomize MAC addresses.

---

# 22. PLAN MODEL

Internet plans must support:

```text
name
price
currency
duration
validity mode
download speed
upload speed
data limit
device limit
simultaneous sessions
idle timeout
session timeout
activation mode
status
```

Plans are business configuration.

Historical purchases must preserve historical commercial evidence.

---

# 23. VALIDITY MODES

The architecture must support at least:

```text
CONTINUOUS
USAGE_TIME
CALENDAR
```

Examples:

### CONTINUOUS

24 hours from activation.

### USAGE_TIME

5 hours total online time consumed across sessions.

### CALENDAR

Valid until midnight or within a defined calendar period.

---

# 24. ACCESS ENTITLEMENT

The entitlement is the right to use internet access.

It is created from:

- paid order
- voucher
- free access
- manual grant
- staff/VIP access

Fields conceptually include:

```text
company
customer
plan
source
status
starts_at
expires_at
allowed seconds
used seconds
allowed data
used data
max devices
activation source
```

---

# 25. ENTITLEMENT STATES

Recommended:

```text
PENDING
ACTIVE
EXHAUSTED
EXPIRED
REVOKED
SUSPENDED
```

Entitlement state is independent from one specific session.

---

# 26. SESSION MODEL

A session represents one network connection period.

One entitlement may produce many sessions.

Fields:

```text
company
hotspot
router
customer
device
entitlement
RADIUS session id
IP
MAC
started_at
last_accounting_at
ended_at
input bytes
output bytes
session seconds
termination reason
status
```

---

# 27. SESSION STATES

Recommended:

```text
AUTHENTICATING
ACTIVE
DISCONNECTED
EXPIRED
TERMINATED
STALE
```

Sessions must not be deleted merely because they are closed.

They are operational/accounting evidence.

---

# 28. AAA ARCHITECTURE

FreeRADIUS is the central AAA component.

Responsibilities:

### Authentication

Who is attempting access?

### Authorization

Does this customer/device have a valid entitlement and what limits apply?

### Accounting

How long and how much data was used?

Flow:

```text
Device
  ↓
MikroTik
  ↓
RADIUS Access-Request
  ↓
FreeRADIUS
  ↓
Entitlement Decision
  ↓
Access-Accept / Reject
```

---

# 29. RADIUS ACCOUNTING FLOW

```text
MikroTik
  ├── Start
  ├── Interim Update
  └── Stop
        ↓
FreeRADIUS
        ↓
Session Processing
        ↓
PostgreSQL
```

Accounting handlers must tolerate:

- duplicates
- retries
- delayed packets
- out-of-order packets
- missing stop packets
- router restarts

---

# 30. PAYMENT ARCHITECTURE

Payment domain is provider-independent.

Core entities:

```text
PaymentProvider
PaymentOrder
PaymentAttempt
PaymentTransaction
PaymentWebhookEvent
Refund
```

One order may have several payment attempts.

---

# 31. PAYMENT FLOW

```text
User selects plan
        ↓
Backend creates order
        ↓
Backend initiates provider request
        ↓
Provider requests payment
        ↓
User approves
        ↓
Provider callback/webhook
        ↓
Backend verifies provider evidence
        ↓
Order marked PAID
        ↓
Entitlement created/activated
        ↓
RADIUS permits access
```

Frontend success screens are never authoritative.

---

# 32. PAYMENT STATES

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

State transitions go through backend services.

---

# 33. PAYMENT PROVIDERS

Architecture must support adapters for:

- M-Pesa
- Airtel Money
- Mixx by Yas
- HaloPesa
- card providers
- bank integrations
- other future providers

Provider-specific logic must not leak through the payment domain.

---

# 34. VOUCHER ARCHITECTURE

Support:

- voucher batches
- single-use vouchers
- expiry
- revocation
- redemption
- plan association
- printable/exportable formats

Voucher redemption must be atomic and concurrency-safe.

---

# 35. FREE ACCESS

The system may support rules such as:

- 15 minutes/day
- 30 minutes/day
- 100 MB/day
- one free trial/device

Free access is still represented as a controlled entitlement.

---

# 36. STAFF ACCESS

Roles include:

- Platform Super Admin
- Company Owner
- Company Admin
- Location Manager
- Operator/Cashier
- Technician

Permissions are explicit.

Location-scoped access is supported.

---

# 37. RBAC

Use:

```text
Role
Permission
UserRole
UserLocationAccess
```

Examples:

```text
routers.view
routers.configure
routers.disconnect_session
payments.view
payments.refund
vouchers.generate
plans.create
reports.financial
staff.manage
```

Backend permissions are authoritative.

---

# 38. SAAS SUBSCRIPTIONS

Tenant subscriptions are separate from hotspot customer payments.

Flow A:

```text
Wi-Fi customer
→ hotspot operator
```

Flow B:

```text
hotspot operator
→ SaaS platform
```

Separate:

```text
SaaSPlan
SaaSSubscription
SaaSInvoice
SaaSPayment
SubscriptionUsage
```

---

# 39. SUBSCRIPTION STATES

Recommended:

```text
TRIAL
ACTIVE
PAST_DUE
SUSPENDED
CANCELLED
EXPIRED
```

Suspension must never silently delete tenant history.

---

# 40. CAPTIVE PORTAL

The Captive Portal is intentionally separate from the business dashboard.

Public flow:

```text
Welcome
↓
Choose Plan
↓
Phone
↓
Payment / Voucher
↓
Pending
↓
Connected
```

It must be:

- mobile-first
- low-bandwidth
- non-technical
- tenant-branded
- fast
- secure

---

# 41. WALLED GARDEN

Before authentication, the hotspot must allow access to only required destinations.

Examples:

- portal domain
- portal API
- payment dependencies
- required static assets
- support/terms resources

Do not unnecessarily expose broad internet access pre-authentication.

---

# 42. API BOUNDARIES

Authenticated SaaS API:

```text
/api/v1/
```

Examples:

```text
/api/v1/locations/
/api/v1/routers/
/api/v1/hotspots/
/api/v1/plans/
/api/v1/customers/
/api/v1/sessions/
/api/v1/payments/
/api/v1/vouchers/
/api/v1/reports/
```

Public portal API:

```text
/api/v1/portal/
```

Payment callbacks:

```text
/api/v1/webhooks/payments/
```

Platform admin APIs may be separately scoped.

---

# 43. BACKEND APPLICATION PATTERN

Business apps should use:

```text
models
services
selectors
api
permissions
exceptions
tests
```

External systems use adapters.

Important rule:

```text
serializers != business services
views != business workflows
```

---

# 44. TRANSACTIONAL CORRECTNESS

Use database transactions for state changes requiring multiple writes.

Critical examples:

- payment confirmation
- entitlement creation
- voucher redemption
- refunds
- subscription renewal
- manual grants

Use locking where concurrency can violate invariants.

---

# 45. IDEMPOTENCY

Must be designed into:

- payment callbacks
- payment confirmation
- voucher redemption
- router provisioning
- RADIUS accounting
- refunds
- subscription renewals
- Celery task retries

External systems must be assumed to retry.

---

# 46. IMMUTABILITY

Do not silently rewrite historical evidence.

Immutable/highly controlled records include:

- confirmed payments
- refunds
- RADIUS/accounting history
- redeemed voucher evidence
- audit events
- subscription invoices

Corrections use explicit compensating actions where appropriate.

---

# 47. AUDIT LOG

Sensitive actions must be audited.

Examples:

- manual entitlement grant
- payment override
- refund
- router configuration
- voucher revocation
- device block
- role change
- tenant suspension

Audit records must never contain secrets.

---

# 48. BACKGROUND PROCESSING

Celery handles asynchronous/repeated work such as:

- router health
- notifications
- report generation
- session reconciliation
- payment follow-up
- subscription renewal
- operational cleanup

Tasks must be idempotent because retries can occur.

---

# 49. ROUTER HEALTH

Backend tracks:

```text
last_seen_at
last_health_at
last_sync_at
```

Status calculation must use thresholds rather than one failed request.

Frontend must be able to distinguish stale status.

---

# 50. DESIRED VS OBSERVED CONFIGURATION

Long-term router management uses:

```text
Desired Configuration
+
Observed Configuration
```

Possible states:

```text
IN_SYNC
DRIFTED
UNKNOWN
```

Changes must be auditable.

---

# 51. SECURITY BASELINE

Mandatory:

- HTTPS
- strong authentication
- RBAC
- tenant isolation
- secure secret storage
- encryption for router credentials
- webhook verification
- rate limiting
- safe CORS
- CSRF controls where applicable
- audit logging
- dependency updates
- database backups
- structured logging
- monitoring

---

# 52. SECRET MANAGEMENT

Secrets include:

- Django secret
- database credentials
- Redis credentials
- router credentials
- payment credentials
- webhook secrets
- RADIUS shared secrets

Never commit secrets to source control.

Never expose them in frontend APIs.

Never log them.

---

# 53. ROUTER SECURITY

Do not expose unrestricted management interfaces publicly.

Preferred:

```text
management VPN
restricted firewall
restricted services
unique management credentials
```

Newer compatible deployments should prefer modern secure connectivity.

---

# 54. DATA PRIVACY

Collect only what is operationally necessary.

Potential data:

- phone number
- device/MAC
- payment evidence
- session times
- usage
- location/hotspot activity

Avoid invasive tracking not needed for service delivery.

Retention policies must distinguish financial, audit, operational and transient logs.

---

# 55. OBSERVABILITY

Monitor:

- API uptime
- API latency
- PostgreSQL
- Redis
- Celery
- FreeRADIUS
- payment callback health
- payment failure rate
- router connectivity
- background queues
- backup status
- disk/resource usage

---

# 56. LOGGING

Structured logs should include relevant correlation identifiers:

```text
request_id
company_id
user_id
router_id
payment_reference
radius_session_id
task_id
```

Sensitive credentials must be redacted.

---

# 57. BACKUPS

Back up:

- PostgreSQL
- application configuration
- RADIUS configuration
- router configuration where appropriate

A backup is not considered reliable until restoration is tested.

---

# 58. REPORTING

Financial reports derive from backend transactional evidence.

Network reports derive from session/accounting evidence.

Core reports include:

### Financial

- daily revenue
- monthly revenue
- revenue by plan
- revenue by location
- revenue by provider
- failed transactions
- refunds

### Network

- active users
- unique users
- session duration
- data usage
- peak times
- router availability

### Vouchers

- generated
- available
- redeemed
- expired
- revoked

---

# 59. EXPORTS

Support:

- CSV
- Excel
- PDF

Exports must be tenant-scoped.

Large exports may use background jobs.

---

# 60. NOTIFICATIONS

Possible channels:

- email
- SMS
- WhatsApp
- push
- in-app

Important events:

- router offline
- router recovered
- subscription expiring
- payment integration issue
- abnormal payment failure rate
- important platform incident

Ordinary successful transactions should not become notification spam.

---

# 61. FRONTEND DESIGN AUTHORITY

Frontend implementation must follow:

```text
FRONTEND_GUIDE.md
UI_DESIGN_SYSTEM.md
WEB_SCREEN_SPECIFICATIONS.md
CAPTIVE_PORTAL_SPECIFICATIONS.md
```

The UI must not look template-generated or vibe-coded.

Architecture correctness does not excuse poor UX, and polished UX does not excuse incorrect backend state.

Both are required.

---

# 62. DEVELOPMENT ENVIRONMENTS

Minimum environments:

```text
Development
Testing/CI
Staging
Production
```

Do not use production systems as the primary development environment.

---

# 63. CONFIGURATION

Environment-specific settings include:

- database
- Redis
- domain
- email
- payment providers
- RADIUS
- object/file storage
- monitoring
- router integration endpoints

Do not hardcode production configuration into source.

---

# 64. DEPLOYMENT CONCEPT

Initial production deployment may use:

```text
Nginx
Gunicorn
Django
PostgreSQL
Redis
Celery Worker
Celery Beat
FreeRADIUS
React static/web deployment
```

These may live on one server initially if resources permit, but architecture must keep services logically separable.

Future scale may split:

- DB
- workers
- RADIUS
- web/API
- monitoring

---

# 65. API AND WORKER FAILURE ISOLATION

A router failure must not crash payment APIs.

A payment-provider outage must not crash router dashboards.

Notification failure must not roll back confirmed payment.

Services must fail independently where possible.

---

# 66. MVP DEFINITION

First commercial MVP includes:

### Core SaaS

- company
- location
- user roles
- router
- hotspot
- customer
- device
- plans

### Access

- entitlements
- sessions
- RADIUS authentication
- RADIUS accounting

### Commerce

- one production payment provider
- payment webhook
- automatic access activation
- voucher generation/redemption

### Operations

- dashboard
- router health
- active sessions
- payments
- customers
- basic reports

### Platform

- multi-tenant isolation
- basic SaaS subscription management
- platform admin

---

# 67. NON-MVP FEATURES

Do not include in first MVP unless architecture is explicitly revised:

- AI analytics
- native mobile app
- loyalty program
- advertising marketplace
- referral program
- reseller hierarchy
- full PPPoE ISP billing
- multi-vendor router support
- automated RouterOS upgrades
- advanced offline mode
- advanced CRM
- sponsored advertising engine
- custom domain automation

---

# 68. IMPLEMENTATION PHASES

## Phase 0 — Foundation

Deliver:

- repositories
- backend baseline
- frontend baseline
- PostgreSQL
- Redis
- Celery
- FreeRADIUS dev environment
- CI
- architecture docs
- coding standards

## Phase 1 — MikroTik Lab

Use current hAP ac lite.

Deliver:

- clean router
- Airtel WAN
- LAN
- Wi-Fi
- DHCP
- NAT
- HotSpot
- local captive login

Acceptance:

```text
Phone joins Wi-Fi
→ captive portal opens
→ login succeeds
→ internet works
```

## Phase 2 — FreeRADIUS

Deliver:

- MikroTik RADIUS client
- Access-Request
- Access-Accept/Reject
- accounting start
- interim updates
- stop
- bandwidth/expiry attributes

## Phase 3 — SaaS Core

Deliver:

- auth
- companies
- locations
- routers
- hotspots
- plans
- customers
- devices
- RBAC
- tenant isolation

## Phase 4 — Entitlements & Sessions

Deliver:

- entitlement lifecycle
- session lifecycle
- RADIUS-backed authorization
- expiry
- device/session limits

## Phase 5 — Captive Portal

Deliver:

- branded portal
- plans
- phone input
- voucher flow
- payment placeholder
- access status

## Phase 6 — Payments

Deliver:

- first provider
- order
- payment attempt
- webhook
- confirmation
- automatic entitlement activation

## Phase 7 — Vouchers

Deliver:

- batches
- codes
- redemption
- expiry
- revocation
- export/print

## Phase 8 — Tenant Dashboard & Reports

Deliver:

- revenue
- active sessions
- customer metrics
- router health
- reports

## Phase 9 — Router Remote Management

Deliver:

- RouterAdapter
- secure connection strategy
- health polling
- disconnect
- sync
- provisioning improvements
- configuration drift

## Phase 10 — Platform Admin

Deliver:

- tenants
- subscriptions
- router fleet
- health
- support
- audits

## Phase 11 — SaaS Billing

Deliver:

- plans
- subscription lifecycle
- invoices
- renewals
- suspension policy

## Phase 12 — Production Hardening

Deliver:

- security review
- tenant isolation review
- load testing
- backup restore test
- payment reconciliation
- RADIUS failure testing
- router security review
- monitoring
- operational runbooks

---

# 69. TESTING STRATEGY

Required layers:

- unit
- service
- API
- integration
- end-to-end
- security
- tenant isolation
- concurrency
- failure-mode testing

Critical end-to-end scenario:

```text
Join Wi-Fi
→ portal
→ choose plan
→ pay
→ verified webhook
→ entitlement
→ RADIUS
→ internet
→ accounting
→ dashboard/report
```

---

# 70. CRITICAL ACCEPTANCE RULES

## Payment retry

Five duplicate callbacks:

```text
1 confirmed payment
1 entitlement
```

## Voucher race

Two simultaneous redemption requests:

```text
1 success
1 rejection
```

## Cross-tenant access

Tenant A requests Tenant B payment:

```text
Denied
```

## Router offline

Historical payments remain unchanged.

## Expired entitlement

New access rejected.

## Duplicate RADIUS interim

Usage not double-counted.

---

# 71. DATA INTEGRITY PRINCIPLES

Never:

- fabricate provider confirmations
- silently edit confirmed payments
- trust browser prices
- infer tenant ownership from user input
- delete accounting history to “clean up”
- overwrite historical plan evidence unintentionally
- ignore concurrency in voucher/payment logic

---

# 72. AGENT IMPLEMENTATION RULES

All coding agents must:

1. read architecture and relevant guides
2. identify domain ownership
3. preserve tenant isolation
4. use explicit services/selectors
5. define transaction boundaries
6. handle retries/idempotency
7. write tests
8. document APIs
9. preserve auditability
10. avoid scope creep

Agents must not begin future phases unless explicitly instructed.

---

# 73. CHANGE CONTROL

Material architecture changes include:

- replacing FreeRADIUS
- changing tenancy model
- changing payment source-of-truth logic
- removing entitlement/session separation
- changing router integration strategy
- introducing a new router vendor
- changing SaaS billing architecture
- changing major deployment topology

Such changes must update this document first.

---

# 74. FINAL ARCHITECTURE RULE

The system is built around this invariant:

```text
Commercial Event
      ↓
Authoritative Backend State
      ↓
Access Entitlement
      ↓
AAA Decision
      ↓
Network Enforcement
      ↓
Accounting Evidence
```

All major features must preserve that chain.

The platform should remain understandable at:

```text
1 router
10 routers
100 routers
1,000 routers
```

without replacing its fundamental domain model.

---

# END OF PROJECT_ARCHITECTURE.md
