# PALP Testing Guide

> Toan bo huong dan chay test, coverage targets, va CI pipeline cho du an PALP.

---

## 1. Overview

### Test Pyramid

PALP su dung 9 lop test, tu nhanh nhat den cham nhat:

```
                    ┌──────────┐
                    │  Load    │  locust -- 50-200 concurrent users
                   ┌┴──────────┴┐
                   │  Recovery  │  backup/restore drill
                  ┌┴────────────┴┐
                  │  Security    │  RBAC, injection, PII checks
                 ┌┴──────────────┴┐
                 │  Data QA       │  integrity, BKT bounds, event completeness
                ┌┴────────────────┴┐
                │  E2E (Playwright) │  7 core journeys, browser-based
               ┌┴──────────────────┴┐
               │  Contract           │  API schema, OpenAPI diff
              ┌┴────────────────────┴┐
              │  Integration          │  DB + Redis + Celery
             ┌┴──────────────────────┴┐
             │  Component (Vitest)     │  React components, hooks
            ┌┴────────────────────────┴┐
            │  Unit (pytest / Vitest)   │  BKT engine, services, utils
            └──────────────────────────┘
```

### Goals

| Metric | Target |
|--------|--------|
| Unit coverage (core modules) | >= 90% |
| Overall coverage | >= 80% |
| E2E core journeys | 100% pass |
| Security checklist | 15/15 pass |
| Data QA checks | 12/12 pass |
| API contract | 46 endpoints covered |

---

## 2. Quick Start

```bash
# Clone and enter project
git clone <repo-url> && cd palp

# Start infrastructure
docker-compose up -d db redis

# Backend (include dev/CI tools: pytest, ruff, mypy, pip-audit)
cd backend
pip install -r requirements.txt -r requirements-dev.txt
pytest

# Frontend
cd ../frontend
npm ci
npm test
```

---

## 3. Backend Tests

### 3.1 Setup

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
```

Configuration is in `pytest.ini`:

```ini
[pytest]
DJANGO_SETTINGS_MODULE = palp.settings.test
addopts =
    --strict-markers
    --tb=short
    --cov=.
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-fail-under=80
```

Services required for integration tests:

| Service | Image | Port |
|---------|-------|------|
| PostgreSQL | postgres:16-alpine | 5432 |
| Redis | redis:7-alpine | 6379 |

Start them with `docker-compose up -d db redis` or let CI handle it.

### 3.2 Run All Tests

```bash
cd backend && pytest
```

### 3.3 Run by Marker

```bash
# Unit tests only (default, excludes marked tests)
pytest -m "not integration and not contract and not security and not load and not data_qa and not recovery"

# Integration tests
pytest -m integration

# API contract tests
pytest -m contract

# Security tests
pytest -m security

# Data quality tests
pytest -m data_qa

# Recovery tests
pytest -m recovery

# Load tests (requires running server)
pytest -m load
```

### 3.4 Run Single App

```bash
pytest accounts/
pytest adaptive/
pytest assessment/
pytest dashboard/
pytest curriculum/
pytest events/
pytest wellbeing/
pytest analytics/
```

### 3.5 Coverage

```bash
# Terminal report
pytest --cov-report=term-missing

# HTML report (opens in browser)
pytest --cov-report=html
open htmlcov/index.html

# Fail if below threshold
pytest --cov-fail-under=90
```

### 3.6 Test Markers

| Marker | Description | Requires |
|--------|-------------|----------|
| *(unmarked)* | Unit tests -- pure logic, no external deps | Nothing |
| `integration` | Full stack with DB + Redis + Celery | PostgreSQL, Redis |
| `contract` | API schema/response validation | PostgreSQL |
| `security` | RBAC, injection, PII encryption | PostgreSQL |
| `load` | Locust performance scenarios | Running server |
| `data_qa` | Data integrity, BKT bounds, event completeness | PostgreSQL |
| `recovery` | Backup/restore, retry logic | PostgreSQL, Docker |
| `slow` | Long-running tests (>10s) | Varies |

### 3.7 Test Settings

Backend tests use `palp.settings.test` which overrides:

- In-memory cache instead of Redis (for unit tests)
- SQLite or test PostgreSQL database
- Celery eager mode (`CELERY_TASK_ALWAYS_EAGER = True`)
- Disabled rate limiting
- Shorter token expiry for fast auth tests

---

## 4. Frontend Tests

### 4.1 Setup

```bash
cd frontend
npm ci
```

### 4.2 Unit / Component Tests (Vitest)

```bash
# Run once
npm run test:run

# Watch mode
npm test

# With coverage
npm run test:cov
```

### 4.3 What to Test

| Layer | Tool | Examples |
|-------|------|---------|
| Hooks | Vitest | `useAuth`, `useMastery`, `usePathway` |
| Components | Vitest + Testing Library | `<AssessmentQuiz>`, `<AlertList>`, `<Dashboard>` |
| Utils | Vitest | formatters, validators, API helpers |
| Stores | Vitest | Zustand/context state transitions |

---

## 5. E2E Tests (Playwright)

### 5.1 Setup

```bash
cd frontend
npx playwright install --with-deps chromium
```

### 5.2 Run

```bash
# All E2E tests
npm run test:e2e

# Specific test file
npx playwright test tests/e2e/login.spec.ts

# Headed mode (see the browser)
npx playwright test --headed

# Debug mode
npx playwright test --debug

# Generate HTML report
npx playwright show-report
```

### 5.3 Core Journeys (must 100% pass)

| Journey | File | Description |
|---------|------|-------------|
| J1 | `student-onboarding.spec.ts` | Register -> consent -> assessment -> learner profile |
| J2 | `student-learning.spec.ts` | Pathway -> submit tasks -> mastery increases |
| J3 | `student-retry.spec.ts` | Fail -> supplementary -> retry -> succeed |
| J4 | `lecturer-warning.spec.ts` | Nightly batch -> alerts RED/YELLOW/GREEN |
| J5 | `lecturer-intervention.spec.ts` | View alert -> take action -> dismiss |
| J6 | `wellbeing-nudge.spec.ts` | 50min continuous -> nudge -> respond |
| J7 | `data-pipeline.spec.ts` | ETL -> cleaning -> KPI computation |

---

## 6. Load Tests (Locust)

### 6.1 Setup

Locust is installed via `requirements.txt`. If not present:

```bash
pip install locust
```

### 6.2 Run

```bash
cd backend
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

Open http://localhost:8089 to configure and start the load test.

### 6.3 CLI mode (headless)

```bash
locust -f tests/load/locustfile.py \
  --host=http://localhost:8000 \
  --users 100 \
  --spawn-rate 10 \
  --run-time 10m \
  --headless \
  --csv=results/load
```

### 6.4 SLO Targets

| Endpoint Group | P95 Target | P99 Target |
|---------------|-----------|-----------|
| `/auth/` | < 500ms | < 1s |
| `/assessment/` (submit/complete) | < 2s | < 3s |
| `/adaptive/submit/` | < 2s | < 3s |
| `/adaptive/mastery/` | < 1s | < 2s |
| `/dashboard/overview/` | < 2s | < 3s |
| `/dashboard/alerts/` | < 1s | < 2s |
| `/events/track/` | < 500ms | < 1s |
| `/events/batch/` | < 2s | < 3s |
| `/health/` | < 200ms | < 500ms |

### 6.5 Load Scenarios

| Scenario | Concurrent Users | Duration | Pass Criteria |
|----------|-----------------|----------|---------------|
| LT-01 Normal | 50 | 10 min | P95 < 3s, 0 errors |
| LT-02 Peak | 100 | 10 min | P95 < 3s, 0 errors |
| LT-03 Stress | 200 | 15 min | P95 < 5s, error rate < 1% |
| LT-04 Spike | 0 -> 200 in 30s | 5 min | Recover within 60s |
| LT-05 Endurance | 50 | 2 hours | No memory leak, P95 stable |

---

## 7. CI Pipeline

PRs must pass the full gate (aligned with QA_STANDARD Section 11 and release ops 17.x):

```
  push/PR ──► lint ────────────────┬──► backend-test ──┬──► e2e ──► build
           ├── migration-check ───┤                   │
           ├── openapi (oasdiff) ─┤                   │
           └── security-audit ────┘                   │
                    └──► frontend-test ───────────────┘
```

| Stage | What it does |
|-------|----------------|
| `lint` | `ruff` + `bandit` on `backend/palp`, `mypy --follow-imports=skip palp`, `npm run lint`, `tsc --noEmit` |
| `migration-check` | `manage.py makemigrations --check --dry-run` |
| `openapi` | `spectacular` + `oasdiff breaking` vs [backend/openapi/schema-baseline.yaml](../backend/openapi/schema-baseline.yaml) |
| `security-audit` | `pip-audit` (backend), `npm audit` (frontend) |
| `backend-test` | pytest tiers + coverage (overall >=80%, core apps >=85%) |
| `frontend-test` | Vitest + coverage |
| `e2e` | Playwright |
| `build` | Docker images + `docker compose -f docker-compose.prod.yml build` |

Optional: **Release gate** — run workflow manually with `run_release_gate=true` (see `scripts/release_gate.py`). **Post-deploy smoke** — [`.github/workflows/release.yml`](../.github/workflows/release.yml) with `BASE_URL`. **Checklists** — `python scripts/release_checklist.py` (pre/post items 17.2 / 17.3).

Pre-commit (optional): [`.pre-commit-config.yaml`](../.pre-commit-config.yaml) — requires `pip install pre-commit` and (for shell hooks) Git Bash on Windows.

Pipeline config: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)

### What Runs Where

| Check | Local (pre-commit) | CI (PR gate) |
|-------|-------------------|-------------|
| `ruff` (palp) | Yes | Yes |
| `bandit` | Optional | Yes |
| `mypy palp` | Optional | Yes |
| `npm run lint` / `tsc` | Yes | Yes |
| Migration check | Optional | Yes |
| OpenAPI breaking diff | Optional | Yes |
| `pip-audit` / `npm audit` | Optional | Yes |
| Unit + integration + contract + security + data_qa + recovery tests | Yes | Yes |
| Frontend unit tests | Yes | Yes |
| E2E (Playwright) | Optional | Yes |
| Docker + prod compose build | No | Yes |

---

## 8. Test Data

Shared fixtures are defined in `backend/conftest.py`:

| Fixture | Type | Description |
|---------|------|-------------|
| `student` | User | Student user (22KT0001) |
| `student_b` | User | Second student (22KT0002) |
| `lecturer` | User | Lecturer user |
| `admin_user` | User | Admin user |
| `student_class` | StudentClass | SBVL-01, 2025-2026 |
| `class_with_members` | StudentClass | Class with 2 students + 1 lecturer |
| `course` | Course | SBVL course |
| `concepts` | List[Concept] | 3 concepts: Noi luc -> Ung suat -> Bien dang |
| `milestones` | List[Milestone] | 2 milestones with concepts |
| `micro_tasks` | List[MicroTask] | 3 tasks across milestones |
| `supplementary` | SupplementaryContent | Text content for concept 1 |
| `assessment` | Assessment | Entry assessment with 3 questions |
| `student_api` | APIClient | Authenticated as student |
| `lecturer_api` | APIClient | Authenticated as lecturer |
| `admin_api` | APIClient | Authenticated as admin |
| `anon_api` | APIClient | Unauthenticated |

---

## 9. Coverage Targets

| Module | Type | Target | Rationale |
|--------|------|--------|-----------|
| `adaptive/` | Unit | >= 90% | Core BKT logic -- sai o day = sai can thiep su pham |
| `assessment/` | Unit | >= 90% | Scoring va learner profile |
| `dashboard/` | Unit | >= 90% | Early warning classification |
| `accounts/` | Unit | >= 90% | Auth + RBAC |
| `curriculum/` | Unit | >= 80% | CRUD, prerequisite graph |
| `events/` | Unit | >= 80% | Event taxonomy |
| `analytics/` | Unit | >= 80% | KPI computation |
| `wellbeing/` | Unit | >= 80% | Nudge trigger |
| **Overall backend** | Combined | >= 80% | `--cov-fail-under=80` in pytest.ini |
| **Frontend** | Unit + Component | >= 75% | Vitest coverage |

---

## 10. Troubleshooting

### Database connection errors

```bash
# Ensure PostgreSQL is running
docker-compose up -d db
# Verify
docker-compose exec db pg_isready -U palp
```

### Redis connection errors

```bash
docker-compose up -d redis
docker-compose exec redis redis-cli ping
```

### Playwright browsers not installed

```bash
cd frontend && npx playwright install --with-deps chromium
```

### Coverage below threshold

```bash
# Check which lines are missed
pytest --cov-report=html
open htmlcov/index.html
```

### Slow tests blocking development

```bash
# Skip slow/integration tests locally
pytest -m "not slow and not integration"
```

---

## References

| Document | Path |
|----------|------|
| QA Standard | [docs/QA_STANDARD.md](QA_STANDARD.md) |
| API Reference | [docs/API.md](API.md) |
| Architecture | [docs/ARCHITECTURE.md](ARCHITECTURE.md) |
| UAT Script | [docs/UAT_SCRIPT.md](UAT_SCRIPT.md) |
| CI Config | [.github/workflows/ci.yml](../.github/workflows/ci.yml) |
| Release smoke | [.github/workflows/release.yml](../.github/workflows/release.yml) |
