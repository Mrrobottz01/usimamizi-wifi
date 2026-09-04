# Multi-Provider SMS Delivery Architecture

This document describes the provider-agnostic SMS delivery engine for **Usimamizi Wi-Fi**.

## 1. Engine Design

```text
[Voucher / Alert Request]
         ↓
 [SMS Queue Service]
         ↓
 [Priority Provider Router]
  ├── Priority 1: Beem Africa Adapter
  ├── Priority 2: RafikiSMS Adapter
  └── Priority 3: NextSMS Tanzania Adapter
         ↓
 [Delivery Attempt Log & Failover Audit]
```

## 2. Phone Normalization

All recipient numbers are processed by `normalize_phone_number()` into E.164 canonical format (`+2557XXXXXXXX`). Provider adapters convert formats (e.g. RafikiSMS stripping `+` to `2557XXXXXXXX`) strictly at provider boundaries.

## 3. Failover Mechanics

Delivery attempts evaluate error categories:
- **Recoverable Errors** (`PROVIDER_UNAVAILABLE`, `TIMEOUT`, `TEMPORARY_PROVIDER_ERROR`, `INSUFFICIENT_BALANCE`, `PROVIDER_RATE_LIMIT`): Triggers failover to next priority provider.
- **Non-Recoverable Errors** (`INVALID_PHONE`, `INVALID_SENDER_ID`, `INVALID_REQUEST`, `AUTHENTICATION_FAILED`): Stops failover loop to prevent wasteful API requests.

## 4. Voucher Decoupling Guarantee

SMS delivery failure **never** invalidates an already-generated voucher.
