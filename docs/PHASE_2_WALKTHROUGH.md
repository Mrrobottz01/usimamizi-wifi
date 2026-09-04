# Phase 2 — Comprehensive Architectural Walkthrough

Complete walkthrough of **Phase 2 — SaaS Plans, Voucher Management & Multi-Provider SMS Delivery**, including the **RafikiSMS Provider & Sender ID Architecture Extension**.

## 1. Domain Overview

Phase 2 establishes the commercial SaaS foundation for **Usimamizi Wi-Fi**, enabling tenants to:
- Define custom commercial internet access plans with rate limits and pricing.
- Generate cryptographically secure voucher batches (`K7PM-4XQ9`).
- Export vouchers to local MikroTik RouterOS `.rsc` import scripts.
- Deliver voucher codes over SMS with multi-provider failover (**Beem Africa**, **RafikiSMS**, and **NextSMS Tanzania**).

## 2. RafikiSMS Integration & Sender ID Architecture

RafikiSMS (`https://api.rafikisms.com`) has been integrated as an active gateway provider with dynamic sender ID discovery:
- **Authentication:** `X-API-Key` header authentication with keys stored in `encrypted_credentials`.
- **Boundary Transformation:** Transforms canonical E.164 (`+255712345678`) to `255712345678` at the adapter boundary.
- **Sender ID Discovery:** Adapter queries `GET /v1/vendor/sender-names` to discover approved brand sender names.
- **Sender Synchronization:** `sync_provider_sender_ids()` caches available sender IDs into `SMSProviderSenderID`, automatically marking vanished senders as unavailable.
- **Provider-Specific Sender Resolution:** Hierarchical resolution rule resolves approved sender IDs independently for each provider during failover (Beem's sender ID is never passed to RafikiSMS).
- **Sender Snapshotting:** Every delivery attempt permanently snapshots the `provider_code` and `sender_id` onto `NotificationDeliveryAttempt`.
- **Length Constraint:** Pre-transmission validation enforces a maximum of 160 characters per SMS.
- **Webhook & Idempotency:** Delivery reports received at `POST /api/v1/webhooks/sms/rafikisms/` use `data.sms_log_id` for idempotency and status transition protection.

## 3. Frozen RADIUS Review

Per architectural directives, all FreeRADIUS code in `backend/apps/radius/` remained **frozen and untouched**. A frozen code review was conducted and documented in [`docs/FROZEN_RADIUS_CODE_REVIEW_NOTES.md`](file:///c:/Users/fsociety/Documents/Usimamizi-wifi/docs/FROZEN_RADIUS_CODE_REVIEW_NOTES.md).
