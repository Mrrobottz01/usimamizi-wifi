# Usimamizi Wi-Fi — Multi-Tenant Hotspot SaaS

A multi-tenant SaaS platform for operating, selling, controlling, and monitoring Wi-Fi hotspot access.

---

## Phase Status Overview

- **Phase 0 — Software Foundation:** **COMPLETE** (Verified with 0 errors)
- **Phase 1 — Local MikroTik Hotspot & Voucher Lab:** **COMPLETE & PHYSICALLY VERIFIED** (Verified on physical hAP ac lite hardware)
- **Phase 2 — SaaS Plans, Voucher Management & Multi-Provider SMS Delivery:** **COMPLETE** (100% verified across backend, Pytest suite, multi-provider SMS failover with Beem, RafikiSMS & NextSMS, RouterOS export, and React frontend)
- **Phase 3 — Access Entitlements & Access Lifecycle:** **COMPLETE & VERIFIED** (Source of truth for customer right-to-access)
- **Phase 4 & 4B — FreeRADIUS Central AAA & Physical Verification:** **COMPLETE & PHYSICALLY VERIFIED** (Centralized Access-Accept/Reject, dynamic bandwidth, Session-Timeout, quotas)
- **Phase 5 — Real-Time Session Control & RADIUS Disconnect:** **COMPLETE & PHYSICALLY VERIFIED** (RFC 3576 Disconnect-Request over UDP 3799)
- **Phase 6 — SaaS Captive Portal & Customer Access Experience:** **COMPLETE & PHYSICALLY VERIFIED** (Tenant-aware mobile-first captive portal, bilingual UX, live simulator)

---

## Project Structure

```text
usimamizi-wifi/
├── backend/                  # Django 5 + DRF + Celery + PostgreSQL backend (Phase 0 Complete)
├── frontend/                 # React 18 + TypeScript + Vite + Tailwind CSS SPA (Phase 0 Complete)
├── infrastructure/
│   └── mikrotik/
│       └── hotspot-portal/   # Low-bandwidth RouterOS Hotspot Captive Portal (Phase 1 Verified)
│           ├── login.html
│           ├── status.html
│           ├── logout.html
│           ├── errors.html
│           └── style.css
├── scripts/
│   └── mikrotik/             # Local lab voucher generator tooling & pytest suite (Phase 1 Verified)
│       ├── generate_vouchers.py
│       └── tests/
│
├── docs/                     # Architectural assessment and phase documentation
│   ├── PHASE_0_ASSESSMENT.md
│   ├── DEVELOPMENT_SETUP.md
│   ├── API_CONVENTIONS.md
│   ├── TESTING_GUIDE.md
│   ├── NOTIFICATIONS_ARCHITECTURE.md
│   ├── MIKROTIK_LAB_BASELINE.md       # Phase 1 RouterOS baseline commands
│   ├── MIKROTIK_LOCAL_HOTSPOT_SETUP.md # Phase 1 Checkpoints A-J guide
│   ├── LOCAL_VOUCHER_BEHAVIOR.md       # RouterOS 6 enforcement mechanics
│   ├── PHASE_1_TEST_RESULTS.md         # Physical test verification matrix (PASSED)
│   └── PHASE_1_WALKTHROUGH.md          # Phase 1 summary & physical verification report
│
├── PROJECT_ARCHITECTURE.md   # Authoritative Master Architecture Baseline
├── BACKEND_GUIDE.md          # Backend Architecture & Agent Implementation Standard
├── FRONTEND_GUIDE.md         # Frontend Architecture & Coding Standard
├── UI_DESIGN_SYSTEM.md       # Visual, Layout, Theme & Component Design System
├── WEB_SCREEN_SPECIFICATIONS.md
├── CAPTIVE_PORTAL_SPECIFICATIONS.md
│
├── README.md
├── .gitignore
├── .env.example
└── docker-compose.yml        # Infrastructure manifest
```

---

## Quickstart

Refer to [`docs/DEVELOPMENT_SETUP.md`](docs/DEVELOPMENT_SETUP.md) for step-by-step local development setup.

### Run All Automated Test Suites
```bash
# Backend pytest suite
& "backend\.venv\Scripts\python.exe" -m pytest backend

# Local voucher generator pytest suite
& "backend\.venv\Scripts\python.exe" -m pytest scripts/mikrotik/tests/

# Frontend typecheck, lint, build, vitest suite
cd frontend && npm run typecheck && npm run lint && npm run build && npm run test
```

### Generate Local Hotspot Vouchers
```bash
& "backend\.venv\Scripts\python.exe" scripts/mikrotik/generate_vouchers.py --profile LAB-15MIN --count 5
```
