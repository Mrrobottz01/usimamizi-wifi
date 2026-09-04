# Testing Guide

**System Name:** Usimamizi Wi-Fi  

---

## 1. Testing Strategy

The platform uses automated testing across both backend and frontend layers:

- **Backend Unit & Service Tests:** Database model invariants, custom user manager, service layer workflows.
- **Backend Tenant Isolation Tests:** API endpoints enforcing multi-company isolation boundaries.
- **Frontend Type & Component Tests:** Vitest component tests, TypeScript strict typechecking, ESLint rules.

---

## 2. Running Backend Tests

Backend tests use `pytest` with `pytest-django`:

```bash
# Execute pytest suite from backend directory
cd backend
python -m pytest
```

---

## 3. Running Frontend Tests

Frontend tests use `vitest` and TypeScript compiler checks:

```bash
cd frontend
npm run typecheck
npm run test
npm run lint
```
