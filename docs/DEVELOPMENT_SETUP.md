# Development Setup Guide

**System Name:** Usimamizi Wi-Fi  
**Document Status:** Standard Development Setup  

---

## 1. Prerequisites

- **Python:** 3.12+
- **Node.js:** v20+ / v26+
- **NPM:** 10+ / 12+
- **Git:** 2.40+

---

## 2. Environment Configuration

Copy `.env.example` to `.env` in the project root:

```bash
cp .env.example .env
```

---

## 3. Backend Setup

From the project root:

```bash
# Create Python virtual environment inside backend directory
python -m venv backend/.venv

# Activate virtual environment
# Windows PowerShell:
.\backend\.venv\Scripts\Activate.ps1

# Install development dependencies
pip install -r backend/requirements/development.txt

# Run migrations
python backend/manage.py migrate

# Run development server
python backend/manage.py runserver 8000
```

Backend API will be available at `http://127.0.0.1:8000/api/v1/`.

---

## 4. Frontend Setup

From the project root:

```bash
cd frontend

# Install Node dependencies
npm install

# Start Vite development server
npm run dev
```

Frontend application will be available at `http://localhost:5173`.

---

## 5. Verification Commands

### Backend Verification
```bash
# Run backend tests
python -m pytest backend

# Check linting
python -m ruff check backend

# Check pending migrations
python backend/manage.py makemigrations --check --dry-run
```

### Frontend Verification
```bash
cd frontend

# Run type check
npm run typecheck

# Run linter
npm run lint

# Run build
npm run build

# Run unit tests
npm run test
```
