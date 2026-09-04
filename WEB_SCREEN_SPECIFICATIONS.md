# WEB_SCREEN_SPECIFICATIONS.md
## Wi-Fi Hotspot Management SaaS
### Tenant SaaS & Platform Admin Screen Specifications

**Version:** 1.0  
**Status:** Mandatory Screen-Level UX Specification  
**Depends on:** `PROJECT_ARCHITECTURE.md`, `FRONTEND_GUIDE.md`, `UI_DESIGN_SYSTEM.md`

---

# 1. Purpose

This document defines what each major web screen must contain, how it should behave and what states must be designed.

Agents must not invent screen structure independently when this specification covers the feature.

---

# 2. Shared Application Shell

All authenticated tenant screens support:

- Light Mode
- Dark Mode
- System Mode

Theme switching belongs in the shared application shell/user preferences and must not be implemented separately per feature.

All authenticated tenant screens use:

- sidebar
- top header
- breadcrumb where useful
- company context
- location context where relevant
- notifications
- user menu

Platform Administration uses a clearly labeled platform context.

---

# 3. Authentication Screens

## 3.1 Login

Purpose:

Authenticate staff users.

Content:

- product logo
- email/phone identifier as selected by auth design
- password
- remember session where appropriate
- Forgot password
- Sign in

States:

- idle
- validating
- loading
- invalid credentials
- account disabled
- subscription/platform access issue where relevant

Do not clutter login with marketing material.

## 3.2 Forgot Password

- identifier field
- submit
- generic success response to avoid account enumeration
- return to login

## 3.3 Reset Password

- new password
- confirmation
- password requirements
- success transition to login

---

# 4. Tenant Onboarding

Use a guided setup.

Steps:

1. Company
2. Location
3. Router
4. Hotspot
5. Plans
6. Payments
7. Launch

Show progress without making onboarding feel like a consumer gamification flow.

---

# 5. Overview Dashboard

## Purpose

Answer:

- Is the business making money?
- Is the hotspot network healthy?
- What needs attention now?

## Header

- Overview
- date range
- location filter
- optional refresh/live status

## KPI row

Recommended:

- Revenue
- Packages Sold
- Users Online
- Routers Online

Each includes relevant comparison/context.

## Main chart

Revenue/activity trend.

Default:

- last 30 days

Allow switching metric where useful, but do not build a chart laboratory.

## Network Health

Show:

- online routers
- degraded routers
- offline routers
- unresolved alerts

## Recent Payments

Columns:

- reference
- customer
- plan
- amount
- provider
- status
- time

## Active Sessions

Compact list/table:

- customer/device
- plan
- location
- connected duration
- usage
- status

## Empty State

If no hotspot launched:

show onboarding status rather than a meaningless zero dashboard.

---

# 6. Locations List

## Purpose

Manage physical operating locations.

## Header

- Locations
- search
- status filter
- Add Location

## Table

Columns:

- name
- code
- region/address summary
- routers
- active users
- status
- manager optional
- actions

## Row click

Open Location Detail.

---

# 7. Location Detail

Header:

- location name
- address/region
- status
- Edit Location

Summary:

- routers
- hotspots
- active users
- today revenue

Sections/Tabs:

- Overview
- Routers
- Hotspots
- Activity
- Settings

Do not overload the first view.

---

# 8. Routers List

## Header

- Routers
- location filter
- status filter
- search
- Add Router

## Table

Columns:

- router name
- identity
- location
- model
- RouterOS
- active sessions
- connection status
- last seen
- actions

Statuses:

- ONLINE
- DEGRADED
- OFFLINE
- PROVISIONING
- FAILED
- UNREGISTERED where relevant

Do not use color alone.

---

# 9. Add Router

Wizard or structured page.

Sections:

## Identity

- router name
- location

## Connection

- router integration method
- management/VPN details as relevant
- credentials through secure form

## Validation

- test connection
- detect model
- detect RouterOS
- detect architecture

## Provisioning

Show explicit steps:

- connection verified
- backup created
- hotspot prerequisites checked
- RADIUS configured
- portal configured
- health check

Do not mark success until backend confirms provisioning.

---

# 10. Router Detail

Header:

- router name
- identity
- status
- location
- Sync
- Diagnostics
- More

Tabs:

- Overview
- Sessions
- Configuration
- Logs

## Overview

Cards/metrics:

- uptime
- CPU
- memory
- active sessions

Connectivity:

- management status
- VPN status if applicable
- last seen
- last sync

Network activity:

- data/session trend where available

Recent events:

- online/offline changes
- sync
- provisioning
- configuration drift

## Sessions

Filtered active/recent sessions for this router.

## Configuration

Show high-level desired and observed state.

Do not expose secrets.

## Logs

Operational logs appropriate to authorized roles.

---

# 11. Router Diagnostics

Purpose:

Help technician understand connection problems.

Show:

- last successful contact
- API connectivity
- RADIUS reachability where known
- VPN state
- provisioning state
- config drift
- recent failures

Actions:

- Retry Connection
- Sync Configuration
- Run Health Check

Technical output may be shown in expandable advanced sections.

---

# 12. Hotspots List

Columns:

- hotspot name
- location
- router
- SSID
- status
- active users
- plans available
- portal status

Action:

- Add Hotspot
- open detail

---

# 13. Hotspot Detail

Header:

- hotspot name
- location
- status
- Preview Portal
- Edit

Tabs:

- Overview
- Plans
- Portal
- Sessions
- Settings

Overview:

- router
- SSID
- active users
- today sales
- portal status
- RADIUS/AAA status summary

---

# 14. Active Sessions

## Purpose

Operational real-time view.

Header:

- Active Sessions
- search
- location
- router
- plan
- status
- refresh/live indicator

Table:

- customer/device
- phone where available
- plan
- location
- router
- IP
- connected since
- usage
- expires
- status
- actions

Actions:

- View
- Disconnect
- Extend Access where permitted
- Block Device

Disconnection requires confirmation.

---

# 15. Session Detail

Header:

- session identity
- ACTIVE/DISCONNECTED/etc.
- Disconnect when permitted

Show:

- customer
- phone
- device
- MAC
- IP
- entitlement
- plan
- router
- hotspot
- started
- last accounting update
- data usage
- session duration
- expiry
- termination reason

Timeline where useful.

---

# 16. Customers List

Header:

- Customers
- search by phone/name
- status filter
- location/activity filters
- Export

Table:

- customer
- phone
- first seen
- last seen
- active plan
- total spent
- devices
- status

Do not require fake CRM fields.

---

# 17. Customer Detail

Header:

- phone/name
- status
- Grant Access
- More

Summary:

- current entitlement
- total spent
- total sessions
- devices
- last seen

Tabs:

- Overview
- Payments
- Sessions
- Devices
- Access History

Manual access grants require reason and audit trail.

---

# 18. Devices List

Columns:

- device name/type where known
- MAC
- customer
- first seen
- last seen
- current session
- status

Actions:

- View
- Block
- Unblock

Warn that randomized MAC addresses may affect continuity.

---

# 19. Device Detail

Show:

- device identity
- linked customer
- MAC
- first seen
- last seen
- sessions
- entitlements used
- block status

Actions:

- Block/Unblock
- reassign customer only if business rules permit

---

# 20. Plans List

Header:

- Plans
- status filter
- Create Plan

Cards or compact table depending count.

Show:

- plan name
- price
- duration
- speed
- data limit
- max devices
- status

Do not use giant colorful pricing cards inside operational admin unless there are very few plans.

---

# 21. Create/Edit Plan

Sections:

## Basic

- name
- description
- price
- currency

## Access

- duration
- validity mode
- speed
- data limit
- max devices
- simultaneous sessions

## Advanced

- idle timeout
- session timeout
- activation mode

## Availability

- active/inactive
- hotspot/location availability if supported

Preview summarized plan before save.

---

# 22. Plan Detail

Show:

- name
- status
- price
- access limits
- locations/hotspots
- packages sold
- revenue
- active entitlements

Actions:

- Edit
- Deactivate
- Duplicate where useful

Historical payments remain tied to the historical plan snapshot/business evidence.

---

# 23. Payments List

## Header

- Payments
- date range
- provider
- status
- location
- plan
- search reference/phone
- Export

## Table

- internal reference
- provider reference
- customer
- plan
- amount
- provider
- status
- created
- confirmed

Financial rows are not normally editable.

---

# 24. Payment Detail

Header:

- payment reference
- status
- amount

Sections:

## Customer

- phone/customer
- plan/order

## Payment

- provider
- provider reference
- amount
- currency
- requested at
- confirmed/failed at

## Access

- entitlement
- activation status

## Timeline

Example:

- order created
- payment requested
- provider callback received
- payment confirmed
- entitlement activated

## Technical Evidence

Authorized users only:

- webhook events
- provider response metadata
- reconciliation state

Never display secrets.

---

# 25. Vouchers

Top-level sections:

- Voucher Batches
- Individual Vouchers where necessary

Header:

- Generate Vouchers
- search
- plan
- status
- expiry

---

# 26. Voucher Batch List

Columns:

- batch reference
- plan
- quantity
- available
- redeemed
- expires
- created by
- created at

Actions:

- View
- Export PDF
- Export Excel
- Revoke Remaining where allowed

---

# 27. Generate Voucher Batch

Fields:

- plan
- quantity
- expiry
- optional label/note

Review:

- total count
- plan
- expiry

Generate only after backend confirmation.

Result:

- download PDF
- export Excel
- print
- view batch

---

# 28. Voucher Batch Detail

Summary:

- plan
- quantity
- available
- redeemed
- expired
- revoked

Table:

- voucher code/display code
- status
- redeemed by
- redeemed at
- expiry

Sensitive full voucher display should follow business security decisions.

---

# 29. Reports

Landing page with purposeful report categories:

## Financial

- Revenue
- Sales by Plan
- Sales by Location
- Sales by Provider
- Refunds/Failures

## Network

- Active Users
- Unique Users
- Session Duration
- Data Usage
- Router Availability

## Vouchers

- Generated
- Redeemed
- Expired
- Revenue where applicable

Shared filters:

- date
- location
- router
- plan
- provider

Exports:

- Excel
- CSV
- PDF where supported

---

# 30. Team

List:

- name
- email/phone
- role
- location access
- status
- last active

Actions:

- Invite
- Edit Role
- Deactivate

---

# 31. Invite Team Member

Fields:

- name optional based account system
- email/phone
- role
- location scope

Preview permissions in plain language.

---

# 32. Settings

Sections:

- Company
- Branding
- Locations
- Payment Providers
- Network Defaults
- Notifications
- Team & Permissions
- Subscription/Billing
- Security

Do not create one enormous settings page.

---

# 33. Payment Provider Settings

Show configured providers:

- M-Pesa
- Airtel Money
- Mixx by Yas
- others

Each shows:

- status
- environment
- last webhook/test
- configuration health

Secrets must be masked.

Test action must not expose credentials.

---

# 34. Branding Settings

Allow:

- company logo
- brand color
- hotspot welcome text
- support phone
- WhatsApp number
- portal image/background within design constraints

Preview Captive Portal.

Tenant customization must not destroy accessibility or layout.

---

# 35. Subscription/Billing Screen

Show:

- current SaaS plan
- status
- renewal date
- usage limits
- routers used
- locations used
- invoices
- payments

If suspended/overdue:

show exact consequences clearly.

---

# 36. Notifications Center

Prioritize:

- router offline
- router recovered
- subscription issue
- failed provider integration
- high payment failure rate
- serious operational alerts

Do not flood with ordinary successful transactions.

---

# 37. Audit Log

Filters:

- actor
- action
- object
- date
- location/company scope

Table:

- timestamp
- actor
- action
- object
- context
- IP optional/authorized

Detail:

- before/after
- metadata

Audit entries are immutable.

---

# 38. Platform Admin Overview

Clearly labeled:

`Platform Admin`

Metrics:

- active companies
- trial companies
- subscriptions
- platform recurring revenue where available
- routers online/offline
- critical system incidents

Operational panels:

- company growth
- subscription state
- router fleet health
- payment integration health
- recent platform alerts

---

# 39. Platform Companies

Table:

- company
- plan
- subscription status
- locations
- routers
- customers
- created
- status

Actions:

- View
- Suspend where authorized
- Support context
- Billing context

Do not allow destructive tenant operations casually.

---

# 40. Platform Company Detail

Sections:

- Overview
- Subscription
- Locations
- Router Fleet
- Payments summary
- Support
- Audit

Cross-tenant support access must be clearly identifiable and audited.

---

# 41. Platform Subscriptions

Show:

- company
- plan
- billing cycle
- status
- next renewal
- amount
- usage

Filters:

- active
- trial
- overdue
- suspended
- cancelled

---

# 42. Router Fleet

Platform-level router table:

- company
- location
- router
- model
- RouterOS
- status
- last seen
- provisioning state

Operational filters:

- offline
- outdated/unsupported version where policy exists
- provisioning failed
- degraded

---

# 43. System Health

Show services:

- API
- database
- Redis
- Celery
- FreeRADIUS
- payment webhooks
- router connectivity subsystem

Each:

- current status
- last check
- latency/queue where meaningful
- incident context

Do not fabricate “99.99%” availability if it is not measured.

---

# 44. Support

Possible later structure:

- tickets
- affected company
- priority
- status
- assigned operator
- router/customer/payment references

Support access to tenant details must be permissioned and audited.

---

# 45. Responsive Requirements

Every list/detail screen must define mobile behavior.

Desktop tables may become:

- stacked rows
- cards
- simplified columns

Primary actions must remain accessible.

Filters collapse into drawer/popover on mobile.

---

# 46. Required States for Every Screen

Every screen must be validated in both Light Mode and Dark Mode.

Every screen must define:

- initial loading
- refresh loading where applicable
- empty
- populated
- recoverable error
- permission denied
- stale data where applicable
- mobile

A screen implementation is incomplete without these states.

---

# 47. Agent Implementation Rule

When implementing any screen from this specification, agents must not add new cards, tabs, charts or decorative elements unless they serve a documented user task.

If backend/API support is missing, agents must clearly surface the missing dependency instead of inventing production behavior.
