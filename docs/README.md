# PALP - Personalized Adaptive Learning Platform

Nền tảng học tập thích ứng cá nhân hóa dành cho sinh viên ĐH Kiến trúc Đà Nẵng.

## Tổng quan

PALP là hệ thống EdTech pilot tập trung vào môn **Sức Bền Vật Liệu**, phục vụ 60-90 sinh viên và 2-3 giảng viên trong 10 tuần pilot. Hệ thống cung cấp:

- **Assessment đầu vào** - xác định năng lực nền và tạo hồ sơ học tập
- **Adaptive Pathway** - lộ trình học thích ứng dựa trên BKT (Bayesian Knowledge Tracing)
- **Micro-task & Milestone** - chia nhỏ kiến thức thành bài tập 5-10 phút
- **Early Warning Dashboard** - cảnh báo sớm cho giảng viên can thiệp kịp thời
- **Wellbeing Nudge** - nhắc nghỉ khi học liên tục quá 50 phút

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | Django 5, Django REST Framework, Celery |
| Database | PostgreSQL 16, Redis 7 |
| Monitoring | Sentry, Health checks |
| Container | Docker, docker-compose |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for local frontend dev)
- Python 3.12+ (for local backend dev)

### 1. Clone & Setup

```bash
git clone <repo-url>
cd palp
cp .env.example .env
```

### 2. Start with Docker

```bash
docker-compose up -d
```

### 3. Initialize Database

```bash
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py shell < ../scripts/seed_data.py
```

### 4. Access

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/api
- API Docs: http://localhost:8000/api/docs/
- Admin: http://localhost:8000/admin/

### Default Accounts

| Role | Username | Password |
|------|----------|----------|
| Admin | admin | admin123456 |
| Lecturer | gv.nguyen | lecturer123 |
| Student | sv001-sv030 | student123 |

## Local Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
palp/
├── backend/           # Django REST API
│   ├── accounts/      # Auth, users, RBAC
│   ├── assessment/    # Entry assessment engine
│   ├── adaptive/      # BKT engine, pathway logic
│   ├── curriculum/    # Courses, concepts, milestones, tasks
│   ├── dashboard/     # Early warning, interventions
│   ├── analytics/     # KPI, reporting
│   ├── events/        # Event tracking
│   └── wellbeing/     # Wellbeing nudges
├── frontend/          # Next.js web application
│   └── src/
│       ├── app/       # Pages (student, lecturer, auth)
│       ├── components/# UI components
│       ├── hooks/     # React hooks
│       ├── lib/       # Utilities, API client
│       └── types/     # TypeScript types
├── scripts/           # Seed data, ETL scripts
├── docs/              # Documentation
└── docker-compose.yml
```

## KPI Targets

| Metric | Target |
|--------|--------|
| Active learning time/week | +20% vs baseline |
| Micro-task completion | >= 70% |
| Student satisfaction (CSAT) | >= 4.0/5 |
| Lecturer dashboard usage | >= 2x/week |

## Tài liệu quy trình & chất lượng

| Tài liệu | Mô tả |
|---------|--------|
| [QA_STANDARD.md](QA_STANDARD.md) | 6 lớp chất lượng, test matrix, release & Go/No-Go |
| [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md) | DoD từng ticket (D1–D12), ma trận N/A |
| [TESTING.md](TESTING.md) | Hướng dẫn chạy test local / CI |

## License

Internal project - ĐH Kiến trúc Đà Nẵng.
