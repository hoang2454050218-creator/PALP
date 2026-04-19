# PALP Project Architecture

## Stack

Modular Django 5.1 monolith + Next.js 14 SPA. Single PostgreSQL 16 database, Redis 7 for cache/broker, Celery workers for async tasks.

```
backend/          Django 5.1, DRF, Celery (palp project)
frontend/         Next.js 14 App Router, TypeScript, Tailwind
infra/            Prometheus + Grafana configs
scripts/          seed_data.py, etl_academic.py, nightly_analytics.py
nginx/            Reverse proxy (prod only)
```

## Django Apps (9 modules)

| App | Prefix | Domain |
|-----|--------|--------|
| accounts | `/api/auth/` | Users, RBAC (Student/Lecturer/Admin), JWT auth, classes |
| assessment | `/api/assessment/` | Entry assessments, questions, submissions |
| adaptive | `/api/adaptive/` | BKT engine, mastery states, student pathways |
| curriculum | `/api/curriculum/` | Courses, concepts, prerequisites, milestones, micro-tasks |
| dashboard | `/api/dashboard/` | Early warning, lecturer dashboard, interventions |
| analytics | `/api/analytics/` | KPIs, reports, ETL, health endpoint (`/api/health/`) |
| events | `/api/events/` | Event logging, learning analytics taxonomy |
| wellbeing | `/api/wellbeing/` | Study-time nudges, wellbeing checks |
| privacy | `/api/privacy/` | Consent, PII encryption, audit, retention, export/delete |

## Key Technical Decisions

- Auth: custom `accounts.User` model, `CookieJWTAuthentication`, JWT in httpOnly cookies
- BKT parameters: `PALP_BKT_DEFAULTS` in settings (P_L0=0.3, P_TRANSIT=0.09, P_GUESS=0.25, P_SLIP=0.10)
- All config via `os.environ.get()` with safe defaults — never hard-code secrets
- Timezone: `Asia/Ho_Chi_Minh`, language: `vi`
- Logging: structured with `request_id`, PII scrub filter
- Privacy middleware: `ConsentGateMiddleware` + `AuditMiddleware` on every request

## Conventions

- Python: snake_case, ruff for linting/formatting
- TypeScript: camelCase variables, PascalCase components
- Database fields: snake_case
- API endpoints: kebab-case URLs, nested under `/api/`
- Test IDs: prefixed by module (`AUTH-*`, `BKT-*`, `EW-*`, `EVT-*`)
- Env vars: UPPER_SNAKE_CASE
- Branches: `main` (release), `develop` (integration)

## Definition of Done (D1–D12)

A work item is **Done** only when all applicable items in `docs/DEFINITION_OF_DONE.md` are satisfied: review, unit + integration + negative tests, analytics events, audit when PII/sensitive, full UI states, basic a11y, monitoring hooks, docs if contracts change, PO + QA sign-off.

Use `.github/PULL_REQUEST_TEMPLATE.md` on every PR. CI job `dod-hints` prints non-blocking reminders.

## Hard "Do NOT" rules

- Hard-code credentials, keys, or environment-specific values
- Break existing API contracts (no removed routes, no type changes, no new required fields without versioning)
- Skip privacy consent checks when accessing PII
- Add dependencies without updating `requirements.txt` or `package.json`
- Write tests that depend on execution order
