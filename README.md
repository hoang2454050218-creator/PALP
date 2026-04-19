# PALP - Personalized Adaptive Learning Platform

PALP là nền tảng học tập thích ứng cá nhân hóa cho bối cảnh pilot giáo dục đại học, hiện được cấu trúc như một monorepo gồm:

- `backend/`: Django 5.1 + Django REST Framework + Celery
- `frontend/`: Next.js 14 App Router + TypeScript + Tailwind CSS
- `docs/`: tài liệu kỹ thuật, vận hành, chất lượng, release
- `infra/`: cấu hình observability, Prometheus alerts, Grafana dashboards
- `nginx/`: reverse proxy cho production
- `scripts/`: seed data, ETL, release gate, checklist, backup helpers

README này là điểm vào chính để hiểu trạng thái hệ thống hiện tại, cách chạy local, surface API chính, và cách lần sang các tài liệu chuyên sâu hơn.

## 1. Hệ thống hiện đang làm gì?

PALP tập trung vào vòng đời học tập thích ứng cho sinh viên:

1. Sinh viên đăng nhập và hoàn thành assessment đầu vào.
2. Backend tạo learner profile và trạng thái mastery theo từng concept.
3. Hệ thống adaptive đề xuất pathway, next task, và ghi nhận task attempts.
4. Dashboard giảng viên tổng hợp cảnh báo sớm, can thiệp, và lịch sử follow-up.
5. Toàn bộ luồng học tập được ghi event để phục vụ analytics, data quality, và release gate.
6. Privacy module quản lý consent, export dữ liệu, xóa dữ liệu, audit log, và retention.

Các tính năng hiện diện trong codebase:

- Assessment đầu vào và learner profile
- Adaptive pathway dựa trên Bayesian Knowledge Tracing (BKT)
- Curriculum theo course, concept, milestone, micro-task, knowledge graph
- Early warning dashboard cho giảng viên
- Event tracking theo taxonomy cố định
- Wellbeing nudge cho học tập liên tục
- Privacy center cho consent, export/delete dữ liệu, incident tracking
- Feature flags và experiments để rollout/analyze hành vi
- Health checks, metrics, backup, release gate, observability hooks

## 2. Kiến trúc tổng thể

```text
Browser
  |
  v
Next.js 14 frontend
  |- App Router UI
  |- /api/* rewrites sang backend
  |- CSP + security headers
  |
  v
Django 5.1 + DRF backend
  |- accounts / assessment / adaptive / curriculum
  |- dashboard / analytics / events / wellbeing
  |- privacy / featureflags / experiments
  |- OpenAPI schema + docs
  |- /api/health/* + /metrics
  |
  +--> PostgreSQL 16
  +--> Redis 7
  +--> Celery worker
  +--> Celery beat
  |
  +--> Sentry (optional, via env)
  +--> Prometheus scrape target (/metrics)
```

### Kiểu kiến trúc

- Backend là **modular Django monolith**, tách theo domain app nhưng dùng chung database.
- Frontend là **Next.js 14 App Router SPA-style shell**, proxy API qua rewrite để giữ cùng origin.
- Hạ tầng dev/prod dùng Docker Compose; production thêm `nginx` và cấu hình cứng hóa bảo mật.
- Observability được tách thành assets trong `infra/` và một compose profile opt-in cho các service hỗ trợ.

## 3. Bản đồ module backend

| App | Prefix | Vai trò |
|-----|--------|---------|
| `accounts` | `/api/auth/` | auth, JWT cookie, profile, classes, consent entrypoint, export/delete cá nhân |
| `assessment` | `/api/assessment/` | danh sách assessment, questions, session, submit answer, complete, learner profile |
| `adaptive` | `/api/adaptive/` | mastery, submit task attempt, pathway, next task, interventions của sinh viên |
| `curriculum` | `/api/curriculum/` | courses, concepts, milestones, knowledge graph, supplementary content, micro-tasks |
| `dashboard` | `/api/dashboard/` | overview lớp, alert list, dismiss alert, intervention history/follow-up |
| `analytics` | `/api/analytics/` | KPI snapshot, KPI registry, lineage, reports, data quality |
| `events` | `/api/events/` | track event, batch tracking, my events, student events |
| `wellbeing` | `/api/wellbeing/` | wellbeing check, nudge response, my nudges |
| `privacy` | `/api/privacy/` | consent history, export, delete, deletion requests, audit log, incidents |
| `featureflags` | `/api/feature-flags/` | active flags cho user hiện tại |
| `experiments` | `/api/experiments/` | assignment map và kết quả thí nghiệm cho admin |
| `analytics.health_urls` | `/api/health/` | liveness, readiness, deep health |

### Các endpoint hệ thống quan trọng

- `GET /api/health/` - liveness
- `GET /api/health/ready/` - readiness cho DB + cache
- `GET /api/health/deep/` - deep health cho admin, bao gồm Celery/queue/error rate
- `GET /api/schema/` - OpenAPI schema
- `GET /api/docs/` - Swagger UI
- `GET /metrics` hoặc `GET /metrics/` - Prometheus metrics endpoint

Lưu ý:

- `/api/schema/` và `/api/docs/` mở khi `DEBUG=True`, nhưng bị giới hạn cho admin ở production.
- `/metrics` có kiểm soát network ở settings, không nên public trực tiếp ra Internet.

## 4. Surface frontend hiện tại

Frontend đang có các route/page chính sau:

- `/login`
- `/dashboard`
- `/assessment`
- `/pathway`
- `/task`
- `/wellbeing`
- `/privacy`
- `/overview`
- `/alerts`
- `/history`
- `/knowledge-graph`
- `/preferences`

Trang gốc `/` hiện dùng để redirect:

- chưa đăng nhập -> `/login`
- lecturer -> `/overview`
- student -> `/dashboard`

Một số điểm đáng chú ý ở frontend:

- Dùng Next.js rewrite để proxy `/api/*` sang backend, giúp browser giữ cùng origin.
- UI xây bằng Tailwind + Radix UI primitives + các component dùng chung trong `frontend/src/components`.
- Global state dùng Zustand.
- Security headers được cấu hình trong `frontend/next.config.js`.
- Frontend có trang privacy center riêng để thao tác consent, export, delete, audit log.

## 5. Tech stack

### Frontend

- Next.js 14
- React 18
- TypeScript 5.5
- Tailwind CSS 3.4
- Radix UI
- Zustand
- Recharts
- Vitest + Testing Library
- Playwright

### Backend

- Django 5.1
- Django REST Framework
- `djangorestframework-simplejwt` với JWT trong httpOnly cookies
- Celery + `django-celery-beat`
- `drf-spectacular` cho OpenAPI
- `django-prometheus`
- `django-axes` cho brute-force protection
- `django-filter`

### Data và hạ tầng

- PostgreSQL 16
- Redis 7
- Docker / Docker Compose
- Gunicorn + Nginx ở production
- Sentry (optional, qua env)
- Prometheus metrics endpoint
- Assets cho Grafana dashboards, Prometheus alerts, Loki, Tempo, Alertmanager

## 6. Cấu trúc repo

```text
.
├── backend/
│   ├── accounts/
│   ├── adaptive/
│   ├── analytics/
│   ├── assessment/
│   ├── curriculum/
│   ├── dashboard/
│   ├── events/
│   ├── experiments/
│   ├── featureflags/
│   ├── palp/
│   ├── privacy/
│   └── wellbeing/
├── frontend/
│   └── src/
│       ├── app/
│       ├── components/
│       ├── hooks/
│       ├── lib/
│       ├── stores/
│       └── types/
├── docs/
├── infra/
│   ├── grafana/
│   ├── observability/
│   └── prometheus/
├── nginx/
├── scripts/
├── docker-compose.yml
├── docker-compose.prod.yml
├── justfile
└── README.md
```

## 7. Chạy nhanh với Docker

### Yêu cầu

- Docker Desktop / Docker Engine
- Docker Compose
- Tùy chọn: `just` nếu muốn dùng task runner trong `justfile`

### 7.1. Tạo file môi trường

```bash
cp .env.example .env
```

Trên Windows PowerShell:

```powershell
Copy-Item ".env.example" ".env"
```

### 7.2. Khởi động full dev stack

```bash
docker compose up -d
```

Hoặc:

```bash
just dev
```

Stack dev chuẩn trong repo gồm:

- `db`
- `redis`
- `backend`
- `celery`
- `celery-beat`
- `frontend`
- `db-backup`

### 7.3. Chạy migration

```bash
docker compose exec backend python manage.py migrate
```

### 7.4. Seed dữ liệu development

Seed script là **dev only** và sẽ từ chối chạy khi `DEBUG=False`.

#### macOS/Linux

```bash
SEED_PASSWORD=Pa55w0rd! docker compose exec -T backend python manage.py shell < scripts/seed_data.py
```

#### Windows PowerShell

```powershell
$env:SEED_PASSWORD = "Pa55w0rd!"
Get-Content -Raw "scripts/seed_data.py" | docker compose exec -T backend python manage.py shell
```

Hoặc dùng shortcut:

```bash
just seed
```

### 7.5. Truy cập

Theo cấu hình mặc định trong compose:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000/api/`
- API docs: `http://localhost:8000/api/docs/`
- OpenAPI schema: `http://localhost:8000/api/schema/`
- Django admin: `http://localhost:8000/admin/`
- Health: `http://localhost:8000/api/health/`
- Metrics: `http://localhost:8000/metrics`

Port thực tế có thể thay đổi nếu bạn override bằng biến môi trường như `FRONTEND_HOST_PORT`, `BACKEND_HOST_PORT`, `POSTGRES_HOST_PORT`, `REDIS_HOST_PORT`.

## 8. Tài khoản seed dữ liệu

Seed script hiện tạo các tài khoản sau:

- `admin`
- `gv.nguyen`
- `sv001` đến `sv030`
- `sv_test`
- `gv_test`

Quy ước password:

- `admin`, `gv.nguyen`, `sv001`-`sv030`: dùng password lấy từ `SEED_PASSWORD`
- `sv_test`, `gv_test`: dùng cố định `testpass123` để phục vụ E2E/dev flows

Seed script cũng tạo:

- course `SBVL`
- 10 concepts
- prerequisite graph
- 6 milestones
- sample micro-tasks
- supplementary content
- entry assessment
- 2 lớp (`22KT1`, `22KT2`)

Không dùng seed data này cho production.

## 9. Chạy local không cần Docker

### 9.1. Backend

```bash
cd backend
python -m venv .venv
```

Kích hoạt môi trường:

```bash
# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Cài dependencies:

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

Trước khi chạy backend ngoài Docker, cần đảm bảo:

- PostgreSQL và Redis đang chạy local hoặc từ container
- `POSTGRES_HOST=localhost` nếu DB không chạy trong Docker network
- `REDIS_URL=redis://localhost:6379/0`
- `CELERY_BROKER_URL=redis://localhost:6379/1`
- `DJANGO_SETTINGS_MODULE=palp.settings.development`

Chạy backend:

```bash
python manage.py migrate
python manage.py runserver
```

### 9.2. Frontend

```bash
cd frontend
npm install
```

Để `npm run dev` hoạt động khi frontend không nằm trong Docker network, hãy set:

```bash
BACKEND_INTERNAL_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

Sau đó chạy:

```bash
npm run dev
```

Nếu không set `BACKEND_INTERNAL_URL`, frontend sẽ mặc định kỳ vọng backend ở hostname `backend`, phù hợp cho Docker hơn là bare-metal dev.

## 10. Khác biệt giữa dev và production

| Hạng mục | Development | Production |
|---------|-------------|------------|
| Backend server | `runserver` | `entrypoint.prod.sh` + Gunicorn |
| Frontend | dev server | `Dockerfile.prod` + `next start` |
| Proxy | truy cập trực tiếp port | Nginx reverse proxy |
| Redis | nhẹ, không persistence bắt buộc | persistence + `maxmemory` + LRU |
| Secrets | có default dev values | bắt buộc set qua env |
| Security | tiện debug | `DEBUG=False`, SSL redirect, secure cookies, HSTS |
| Docs/schema | mở khi debug | admin-only |
| Backup | container `db-backup` theo chu kỳ | container `backup` chạy script giữ retention |

Production Compose hiện yêu cầu tối thiểu:

- `DJANGO_SECRET_KEY`
- `POSTGRES_PASSWORD`
- `PII_ENCRYPTION_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `CORS_ALLOWED_ORIGINS`

## 11. Bảo mật và quyền riêng tư

Các quyết định bảo mật hiện diện trong codebase:

- JWT được quản lý bằng **httpOnly cookies**, không dựa vào localStorage.
- Middleware `ConsentGateMiddleware` chặn truy cập PII trước khi có consent hợp lệ.
- Middleware `AuditMiddleware` ghi audit với các prefix nhạy cảm.
- PII được mã hóa tại rest qua `PII_ENCRYPTION_KEY`.
- `django-axes` bảo vệ brute-force login và hỗ trợ ngưỡng captcha.
- Next.js cấu hình CSP, `X-Frame-Options`, `nosniff`, HSTS, referrer policy, permissions policy.
- Auth endpoints có throttling (`login`, `register`, `export`, `assessment_submit`).
- Production scrub PII khỏi logs và Sentry events.

Nếu bạn thêm endpoint mới có truy cập PII, hãy kiểm tra lại:

1. RBAC có đúng cho student / lecturer / admin không?
2. Endpoint có cần đưa vào danh sách audit sensitive prefixes không?
3. Endpoint có bị consent gate chặn đúng lúc không?
4. Response và log có làm lộ PII hay secret không?

## 12. Adaptive learning và early warning

### Adaptive engine

Backend hiện có cấu hình BKT mặc định trong settings:

- `P_L0 = 0.3`
- `P_TRANSIT = 0.09`
- `P_GUESS = 0.25`
- `P_SLIP = 0.10`

Ngưỡng adaptive:

- `MASTERY_LOW = 0.60`
- `MASTERY_HIGH = 0.85`
- `MIN_ATTEMPTS_FOR_ADVANCE = 3`

### Early warning

Rule cấu hình mặc định:

- inactivity vàng sau `3` ngày
- inactivity đỏ sau `5` ngày
- retry failure threshold là `3`

Deep health và analytics hiện còn theo dõi:

- queue backlog theo từng Celery queue
- error rate so với SLO
- heartbeat của Celery Beat
- backup age / restore drill freshness

## 13. Observability và vận hành

### Health endpoints

- `GET /api/health/` -> liveness
- `GET /api/health/ready/` -> DB + cache readiness
- `GET /api/health/deep/` -> admin deep health

### Metrics

- Django expose Prometheus metrics qua `/metrics`
- Repo có Prometheus config và alert rules trong `infra/prometheus/`
- Repo có Grafana dashboard provisioning trong `infra/grafana/`

### Observability profile

Repo hiện có compose profile/stack cho:

- Loki
- Promtail
- Alertmanager
- Tempo
- PgBouncer

Khởi động bằng compose override của observability stack:

```bash
docker compose -f docker-compose.yml -f infra/observability/docker-compose.observability.yml --profile observability up -d
```

Nếu bạn đã quen workflow bằng `justfile`, repo cũng có recipe `just observability`.

### Backup và release gate

- Dev stack có `db-backup` tạo backup định kỳ và giữ lại số bản dump gần nhất.
- Prod stack có service `backup` chạy `scripts/backup_db.sh`.
- Release gate có script `scripts/release_gate.py`.
- Checklist release có trong `scripts/release_checklist.py`.

## 14. Testing và quality gates

### Backend

```bash
cd backend
pytest
```

Hoặc cài đầy đủ dev tools:

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

Markers đang được dùng:

- `integration`
- `contract`
- `security`
- `load`
- `data_qa`
- `recovery`
- `slow`

### Frontend

```bash
cd frontend
npm install
npm run test:run
```

### E2E

```bash
cd frontend
npm run test:e2e
```

### Lint và type-check

Backend:

```bash
cd backend
ruff check .
ruff format --check .
mypy --follow-imports=skip palp
```

Frontend:

```bash
cd frontend
npm run lint
npx tsc --noEmit
```

### Shortcut commands

Nếu dùng `just`:

- `just test`
- `just test-backend`
- `just test-frontend`
- `just test-e2e`
- `just lint`
- `just release-gate`
- `just health`

## 15. Biến môi trường quan trọng

Xem đầy đủ trong `.env.example`. Những biến quan trọng nhất:

| Nhóm | Biến |
|------|------|
| Django | `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_SETTINGS_MODULE`, `DJANGO_ALLOWED_HOSTS` |
| Database | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` |
| Redis/Celery | `REDIS_URL`, `CELERY_BROKER_URL` |
| JWT | `JWT_ACCESS_TOKEN_LIFETIME_MINUTES`, `JWT_REFRESH_TOKEN_LIFETIME_DAYS` |
| Privacy | `PII_ENCRYPTION_KEY` |
| CORS | `CORS_ALLOWED_ORIGINS` |
| Frontend | `NEXT_PUBLIC_API_URL`, `BACKEND_INTERNAL_URL` |
| Sentry | `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `SENTRY_TRACES_SAMPLE_RATE`, `SENTRY_PROFILES_SAMPLE_RATE` |
| Ops | `QUEUE_ALERT_WARN`, `QUEUE_ALERT_CRITICAL`, `BACKUP_RETENTION_DAYS` |
| Seed | `SEED_PASSWORD` |

## 16. Tài liệu nên đọc tiếp

### Để hiểu kiến trúc

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md)
- [`docs/API.md`](docs/API.md)
- [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md)

### Để chạy test và release

- [`docs/TESTING.md`](docs/TESTING.md)
- [`docs/QA_STANDARD.md`](docs/QA_STANDARD.md)
- [`docs/DEFINITION_OF_DONE.md`](docs/DEFINITION_OF_DONE.md)
- [`docs/RELEASE_RUNBOOK.md`](docs/RELEASE_RUNBOOK.md)
- [`docs/RELEASE_GATE_QUICKREF.md`](docs/RELEASE_GATE_QUICKREF.md)
- [`docs/MIGRATION_RUNBOOK.md`](docs/MIGRATION_RUNBOOK.md)

### Để hiểu quyết định kỹ thuật

- [`docs/adr/README.md`](docs/adr/README.md)

Các ADR hiện có bao gồm:

- JWT cookie / httpOnly
- BKT vs DKT
- Celery vs Kafka
- Fernet vs pgcrypto
- Compose pilot vs k8s phase 2
- Next.js App Router
- Spectacular + oasdiff
- PgBouncer transaction pooling

## 17. Trạng thái README này

README này được viết lại để phản ánh trạng thái repo hiện tại:

- Có root README làm điểm vào chính
- Đồng bộ với các app Django thật sự có trong `INSTALLED_APPS`
- Đồng bộ với các route đang được mount trong `backend/palp/urls.py`
- Đồng bộ với Docker Compose dev/prod, seed script, testing stack, security và observability assets

Nếu bạn muốn chi tiết theo từng mảng hơn nữa, hãy tiếp tục từ thư mục `docs/`.
