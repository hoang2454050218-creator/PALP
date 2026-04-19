# PALP — Personalized Adaptive Learning Platform

Single source of truth cho mọi AI coding agent. Tất cả file `.md` trong thư mục này được Ruler concat và phân phối tới Cursor, Claude Code, GitHub Copilot, OpenAI Codex, Gemini CLI, Aider, Windsurf, Warp, Junie, Roo, Kilo, Trae, Kiro, Zed, Goose, Amp, OpenCode, Antigravity, Factory Droid, Mistral Vibe, Pi, Jules, Qwen, Crush, Cline, AmazonQ, AugmentCode, Firebase Studio, Open Hands, Firebender, JetBrains AI.

## TL;DR cho agent mới vào dự án

PALP là Django 5.1 monolith + Next.js 14 SPA, PostgreSQL 16, Redis 7, Celery. Phục vụ học tập cá nhân hoá dựa trên Bayesian Knowledge Tracing (BKT). Backend ở `backend/`, frontend ở `frontend/`, infra ở `infra/`, scripts ở `scripts/`.

## Nguyên tắc tối thượng

1. **Không hard-code** — mọi config qua `os.environ.get()` (backend) hoặc `process.env.NEXT_PUBLIC_*` (frontend).
2. **Không phá API contract** — không xoá route, không đổi response type, không thêm required field mà không version.
3. **Không bỏ consent check** — endpoint chạm PII bắt buộc qua `ConsentGateMiddleware`.
4. **Không thêm dependency** mà không update `requirements.txt` / `package.json`.
5. **Không viết test phụ thuộc thứ tự thực thi** — mỗi test độc lập.

## File trong thư mục này (đọc theo thứ tự)

| File | Phạm vi |
|------|---------|
| `01-project-architecture.md` | Module map, 9 Django apps, key technical decisions |
| `02-django-backend.md` | Django 5/DRF/Celery patterns |
| `03-nextjs-frontend.md` | Next.js 14 App Router/Tailwind/Radix |
| `04-api-conventions.md` | REST design, RBAC, throttling, OpenAPI |
| `05-testing-standards.md` | pytest/Vitest/Playwright markers, fixtures, coverage targets |
| `06-privacy-security.md` | PII encryption, consent, audit, RBAC, 15-item security checklist |
| `07-docker-ops.md` | Docker compose, monitoring, backup, healthcheck |
| `08-coding-standards.md` | Universal coding standards (clean code, SRP, no duplication) |

## Skills (progressive disclosure)

Skills nằm ở `.ruler/skills/` được Ruler copy sang `.cursor/skills/`, `.claude/skills/`, `.codex/skills/`, v.v. Agent tự kích hoạt theo ngữ cảnh — đọc `.ruler/skills/INDEX.md` để discovery nhanh.

### Foundational (existing)

| Skill | Trigger |
|-------|---------|
| `bkt-engine` | Sửa BKT engine, mastery state, pathway |
| `privacy-gate` | Thêm endpoint chạm PII, consent + audit + encryption |
| `rbac-check` | Thêm `APIView`/`ViewSet`, `get_queryset`, RBAC validation |
| `release-gate` | Chuẩn bị release, chạy `scripts/release_gate.py`, D1-D12 |
| `event-taxonomy` | Phát `EventLog`, thêm `event_name` mới |
| `migration-runbook` | Tạo Django migration zero-downtime |
| `frontend-component` | Tạo React component (Radix + cva + Tailwind + a11y) |
| `celery-task` | Thêm Celery task idempotent + retryable |
| `incident-response` | Triage P0/P1, post-mortem, 48h SLA |
| `openapi-update` | Sửa DRF view/serializer, oasdiff baseline |
| `pr-review` | Review PR (9-pass playbook) |

### v3 Roadmap (P0–P6 — AI-Coach upgrade)

13 skills mới. Đọc kèm [`docs/AI_COACH_ARCHITECTURE.md`](../docs/AI_COACH_ARCHITECTURE.md) cho context.

| Skill | Phase | Trigger |
|-------|-------|---------|
| `causal-experiment` | P0 | A/B với uplift/CUPED/DR; trước mọi feature rollout |
| `fairness-audit` | P0 | Trước deploy ML/clustering; CI gate per release |
| `signals-pipeline` | P1 | Sửa `frontend/src/lib/sensing/`, `backend/signals/`, signal taxonomy |
| `risk-scoring` | P1 | Sửa weights/components RiskScore, integration `compute_early_warnings` |
| `peer-engine` | P3 | Sửa `backend/peer/` (cohort, reciprocal match, herd cluster, frontier) |
| `coach-safety` | P4 | Sửa `backend/coach/llm/`, system prompts, tool registry, guardrails |
| `llm-routing` | P4 | Sửa intent detection, cloud/local routing rules |
| `emergency-response` | P4 | Sửa `backend/emergency/`, counselor flow, escalation 15-min SLA |
| `dkt-engine` | P5 | Sửa `backend/dkt/`, SAKT/AKT training, shadow vs BKT v2 |
| `xai-interpretation` | P6 | Thêm/sửa explanation cho ML model (SHAP/attention/counterfactual) |
| `spaced-repetition` | P6 | Sửa `backend/spacedrep/`, FSRS scheduler, CLT tuning, ZPD scaffolding |
| `affect-analysis` | P6 | Sửa `backend/affect/`, keystroke/linguistic/facial 3-tier consent |
| `instructor-copilot` | P6 | Sửa `backend/instructor_copilot/`, auto-generate/grade/feedback drafts |

### Apps mới sẽ được tạo (v3 roadmap)

| Phase | App path | Vai trò |
|-------|----------|---------|
| P0 | `backend/mlops/` | Feast + MLflow + Evidently + shadow deployment |
| P0 | `backend/causal/` | Uplift modeling, CUPED, doubly-robust |
| P0 | `backend/fairness/` | fairlearn intersectional audit |
| P0 | `backend/sessions/` | Device fingerprint + multi-device session linking |
| P1 | `backend/signals/` | Behavioral signal ingest + rollup |
| P1 | `backend/risk/` | RiskScore 5-dim composite |
| P2 | `backend/goals/` | Zimmerman SRL 3-phase cycle |
| P3 | `backend/peer/` | Cohort + reciprocal teaching + herd cluster |
| P4 | `backend/coach/` | LLM orchestration, dual routing, memory, tools |
| P4 | `backend/emergency/` | Detection + counselor queue + escalation + follow-up |
| P4 | `backend/notifications/` | SSE + Web Push + Email dispatcher |
| P5 | `backend/dkt/` | SAKT/AKT transformer Deep Knowledge Tracing |
| P5 | `backend/bandit/` | Thompson sampling contextual MAB |
| P5 | `backend/survival/` | Cox PH + DeepHit dropout prediction |
| P6 | `backend/explainability/` | SHAP + attention + counterfactual XAI |
| P6 | `backend/spacedrep/` | FSRS + CLT + ZPD + Deliberate Practice |
| P6 | `backend/privacy_dp/` | Opacus DP-SGD + Flower federated |
| P6 | `backend/affect/` | Keystroke + linguistic + facial (on-device) |
| P6 | `backend/instructor_copilot/` | Auto-generate exercises/grade/feedback drafts |

### Tài liệu chuyên đề mới (`docs/`)

13 docs mới + model_cards directory cho v3 roadmap.

| Doc | Vai trò |
|-----|---------|
| [AI_COACH_ARCHITECTURE.md](../docs/AI_COACH_ARCHITECTURE.md) | 7-layer architecture, sequence diagrams |
| [SIGNAL_TAXONOMY.md](../docs/SIGNAL_TAXONOMY.md) | 25+ event mới, JSON schemas |
| [PEER_ENGINE_DESIGN.md](../docs/PEER_ENGINE_DESIGN.md) | Anti-herd + reciprocal teaching design |
| [COACH_SAFETY_PLAYBOOK.md](../docs/COACH_SAFETY_PLAYBOOK.md) | LLM 9-layer defense |
| [PRIVACY_V2_DPIA.md](../docs/PRIVACY_V2_DPIA.md) | DPIA cho 14 consent types mới |
| [MOTIVATION_DESIGN.md](../docs/MOTIVATION_DESIGN.md) | SDT principles, anti-gamification rules |
| [EMERGENCY_RESPONSE_TRAINING.md](../docs/EMERGENCY_RESPONSE_TRAINING.md) | Mental health crisis pipeline + counselor training |
| [RED_TEAM_PLAYBOOK.md](../docs/RED_TEAM_PLAYBOOK.md) | Quarterly LLM security exercise |
| [LEARNING_SCIENCE_FOUNDATIONS.md](../docs/LEARNING_SCIENCE_FOUNDATIONS.md) | Multi-theory mapping với citations |
| [DIFFERENTIAL_PRIVACY_SPEC.md](../docs/DIFFERENTIAL_PRIVACY_SPEC.md) | DP threat model, Opacus + Flower |
| [COLD_START_PLAYBOOK.md](../docs/COLD_START_PLAYBOOK.md) | New/transfer/returning student playbooks |
| [INCIDENT_CULTURE.md](../docs/INCIDENT_CULTURE.md) | Blameless postmortem + Responsible Disclosure |
| [MULTISTAKEHOLDER_GUIDE.md](../docs/MULTISTAKEHOLDER_GUIDE.md) | 5 stakeholder roles guide |
| [PUBLICATION_ROADMAP.md](../docs/PUBLICATION_ROADMAP.md) | LAK/AIED/EDM publication plan |
| [model_cards/](../docs/model_cards/) | Model Cards + Datasheets per ML model |

## Nguyên tắc bổ sung cho v3 roadmap

Các nguyên tắc 1-5 ở trên (không hard-code, không phá API contract, không bỏ consent check, không thêm dependency thiếu update, không test phụ thuộc thứ tự) áp dụng tuyệt đối. Bổ sung 3 nguyên tắc cho v3:

6. **Causal-not-correlational** — không ship feature/model nào không có A/B với uplift estimator (P0). Xem [causal-experiment skill](skills/causal-experiment/SKILL.md).
7. **SDT-aligned, no extrinsic gamification** — TUYỆT ĐỐI không points/badges/leaderboard/streak. Xem [MOTIVATION_DESIGN.md](../docs/MOTIVATION_DESIGN.md).
8. **Fairness-by-design + Explainable-by-default** — mọi ML/clustering qua fairness audit + có explanation interface. Xem [fairness-audit skill](skills/fairness-audit/SKILL.md) và [xai-interpretation skill](skills/xai-interpretation/SKILL.md).

## Workflow khi sửa rules

1. Edit file `.md` trong `.ruler/`
2. `npm run ruler:apply` (hoặc pre-commit hook tự chạy)
3. Commit cả `.ruler/*` lẫn các file Ruler sinh tự động (nếu chưa bị `.gitignore`)
4. CI `ruler-check.yml` sẽ fail nếu drift

Chi tiết: xem `CONTRIBUTING.md` section "AI Agent Rules (Ruler)".
