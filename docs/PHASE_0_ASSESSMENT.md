# Phase 0 Assessment — Software Foundation

**System Name:** Usimamizi Wi-Fi  
**Document Status:** Complete Assessment Baseline  
**Date:** August 2026  

---

## 1. Current Repository State

Upon inspecting the repository `c:\Users\fsociety\Documents\Usimamizi-wifi`:

- **Directory Structure:** Top-level workspace contains only specification and guide documents.
- **Specification Files Present:**
  1. `PROJECT_ARCHITECTURE.md` (30.4 KB) — Master Product, System & Technical Architecture Baseline.
  2. `BACKEND_GUIDE.md` (38.1 KB) — Backend Architecture, Domain Rules & Agent Implementation Standard.
  3. `FRONTEND_GUIDE.md` (16.0 KB) — Frontend Architecture, Coding Standards & SPA Design.
  4. `UI_DESIGN_SYSTEM.md` (15.3 KB) — Visual, Layout, Theme & Component Design System.
  5. `WEB_SCREEN_SPECIFICATIONS.md` (15.1 KB) — Detailed UI/UX Specifications for Tenant Dashboard & Platform Admin.
  6. `CAPTIVE_PORTAL_SPECIFICATIONS.md` (15.2 KB) — Wi-Fi Captive Portal User Experience & Technical Specification.
- **Codebase Initialization:** The repository is **partially initialized** (specification docs only). No application source code (`backend/` or `frontend/`), configuration files, or infrastructure manifests (`docker-compose.yml`, `.gitignore`, `README.md`) currently exist.
- **Useful Work Assessment:** All existing `.md` files are authoritative project specifications and MUST be preserved in the root directory.

---

## 2. Architecture Fit

The target architecture outlined in `PROJECT_ARCHITECTURE.md` establishes a clean, decoupled multi-tenant Wi-Fi Hotspot Management platform.

### Target Alignment:
- **Monorepo Structure:** Preserving the project root with `backend/`, `frontend/`, `docs/`, `infrastructure/`, and `scripts/`.
- **Backend Stack:** Django 5.x, Django REST Framework (DRF), PostgreSQL, Redis, Celery, and Celery Beat.
- **Frontend Stack:** React 18 / 19, TypeScript, Vite, Tailwind CSS, Lucide icons, and Radix UI / custom primitives.
- **Data & Commercial Integrity:** Database is authoritative for business state, payments, vouchers, customer entitlements, and multi-tenant isolation.
- **Decoupled Integrations:** Notifications use an extensible adapter pattern (`SMSProviderAdapter`) ready for future tenant/platform provider binding without risking live SMS credentials in Phase 0.

---

## 3. Proposed Phase 0 Changes

### A. Repository & Directory Structure
- Create `backend/`, `frontend/`, `docs/`, `infrastructure/`, and `scripts/`.
- Create top-level `README.md`, `.gitignore`, `.env.example`, and `docker-compose.yml`.

### B. Backend Foundation (`backend/`)
- Initialize Django project with modular settings (`config/settings/base.py`, `development.py`, `test.py`, `production.py`).
- Implement core backend domain apps:
  - `apps.accounts`: Custom `User` model (`email` primary, `phone`, `first_name`, `last_name`, timestamped).
  - `apps.companies`: `Company` model (`name`, `slug`, `country`, `currency`, `timezone`, `status`), and `CompanyMembership` model (`company`, `user`, `is_active`).
  - `apps.notifications`: Notification models (`NotificationTemplate`, `NotificationMessage`, `NotificationProviderConfiguration`), message lifecycle states (`QUEUED`, `SENDING`, `SENT`, `DELIVERED`, `FAILED`), and `SMSProviderAdapter` interface hierarchy.
  - `apps.audit`: `AuditLog` model for action logging.
- Architecture Conventions: Enforce `services/`, `selectors/`, `api/` (serializers, views, urls), `permissions.py`, `exceptions.py`, and `tests/` in domain apps.
- API Endpoints:
  - `GET /api/v1/health/` (Health check returning system status, DB & Redis connectivity)
  - `POST /api/v1/accounts/auth/login/`, `POST /api/v1/accounts/auth/logout/`, `GET /api/v1/accounts/auth/me/`
  - `GET /api/v1/companies/`, `GET /api/v1/companies/{id}/`
- Tenant Isolation: Scoped queryset evaluation in selectors and DRF permissions enforcing strict company isolation. Cross-tenant access fails with 403 Forbidden.
- Error Response Standard: Unified JSON error responses (`code`, `detail`, `field_errors`).

### C. Frontend Foundation (`frontend/`)
- Initialize React + TypeScript application using Vite.
- Configure Tailwind CSS with semantic design tokens supporting Light, Dark, and System modes.
- Implement Theme Provider with persistent preference (`localStorage`) and system media query listener (`prefers-color-scheme`), guaranteeing zero theme-flash.
- Shared UI Primitives: `Button`, `Input`, `Select`, `Checkbox`, `Badge`, `Card`, `Dialog`, `Dropdown`, `Tabs`, `Table`, `Skeleton`, `Alert`, `EmptyState`, `Toast`.
- Authenticated Application Shell: Responsive sidebar, top header, page container, theme selector, user menu, company context switcher. Real empty states where backend data is absent.
- Settings Screen Structure: Navigation for `Company`, `Branding`, `Notifications` (visual slots for SMS, Email, WhatsApp), and `Security`.
- Authentication Context & Router: Login screen, auth state management (JWT/Token storage), protected route wrappers.

### D. Async Tasks & Services Configuration
- Configure Celery & Redis connection in backend.
- Add diagnostic Celery task (`health_check_task`) to verify worker functionality.
- Set up Docker Compose containing `postgres`, `redis`, `backend`, `celery-worker`, and `celery-beat`.

### E. Code Quality, Testing & CI
- Backend: `pytest`, `pytest-django`, `ruff` configuration.
- Frontend: ESLint, Prettier, TypeScript strict mode (`tsconfig.json`).
- GitHub Actions CI workflow (`.github/workflows/ci.yml`) running backend lint/tests/migration check and frontend lint/typecheck/build/tests.

### F. Documentation
- `docs/PHASE_0_ASSESSMENT.md` (this document)
- `docs/DEVELOPMENT_SETUP.md`
- `docs/API_CONVENTIONS.md`
- `docs/TESTING_GUIDE.md`
- `docs/NOTIFICATIONS_ARCHITECTURE.md`

---

## 4. Dependencies

### Backend Dependencies (`requirements/base.txt`, `development.txt`, `test.txt`)
- Python 3.12+
- Django 5.1+
- djangorestframework 3.15+
- djangorestframework-simplejwt 5.3+
- psycopg[binary] 3.2+
- redis 5.0+
- celery 5.4+
- django-cors-headers 4.4+
- django-environ 0.11+
- pytest 8.3+, pytest-django 4.9+, ruff 0.6+

### Frontend Dependencies (`frontend/package.json`)
- React 18 / 19
- TypeScript 5.5+
- Vite 5+
- Tailwind CSS 3.4+ / 4+
- Lucide React icons
- React Router DOM 6+ / 7+
- Axios / Fetch API wrapper

---

## 5. Risks & Mitigation

| Risk | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| Cross-tenant data leakage | High | Enforce mandatory company scoping in backend `selectors/` and DRF custom `IsCompanyMember` permission classes. Unit tests verify 403 response on cross-tenant requests. |
| Business logic in views/serializers/signals | Medium | Enforce service/selector layer pattern explicitly across all Django apps. |
| Theme flash on frontend initial load | Low | Apply script tag theme resolution in `index.html` before rendering React DOM. |
| Environment credentials leak | High | Exclude secrets from repository via `.gitignore` and enforce `.env.example` placeholders. |

---

## 6. Assumptions
1. Phase 0 requires no live integrations with MikroTik, FreeRADIUS, mobile money gateways, or external SMS providers.
2. PostgreSQL 16+ and Redis 7+ are used in local Docker development.
3. Authentication for SPA communication uses JWT tokens (`/api/v1/accounts/auth/token/` & refresh) or DRF Token Authentication.

---

## 7. Deviations from Default Assumptions
- None. Phase 0 strictly follows all rules defined in `PROJECT_ARCHITECTURE.md` through `CAPTIVE_PORTAL_SPECIFICATIONS.md`.
