# PALP - Sprint Plan & Delivery Roadmap

## Timeline Overview

```
W1-W2  │ Sprint 1: Foundation & Assessment
W3-W4  │ Sprint 2: Adaptive Pathway & Micro-task Flow
W5-W6  │ Sprint 3: Lecturer Dashboard & Event Pipeline
W7-W8  │ Sprint 4: UAT, Hardening & Launch Prep
W9-W10 │ Sprint 5: Pilot Run & Reporting
W11-W16│ Post-pilot: Analysis, Report, Decision Gate 3
```

## Sprint 1 (W1-W2): Foundation & Assessment

**Goal**: Infrastructure setup, auth, and entry assessment working end-to-end.

| Task | Priority | Acceptance Criteria |
|------|----------|-------------------|
| Docker environment | P0 | All services start with `docker-compose up` |
| Django project skeleton | P0 | All 8 apps created with models |
| Database migrations | P0 | All tables created, seed data loadable |
| JWT auth flow | P0 | Login, refresh, protected routes working |
| RBAC (3 roles) | P0 | Student/lecturer/admin permissions enforced |
| Next.js project | P0 | Login page, routing, API client |
| Assessment engine API | P0 | Start, answer, complete flow working |
| Assessment UI | P0 | Quiz with timer, save progress |
| LearnerProfile generation | P0 | Profile created on assessment completion |
| Knowledge graph seed | P1 | 10 concepts with prerequisites for SBVL |
| Event tracking (session, assessment) | P1 | Events stored in database |
| ETL script skeleton | P2 | Script structure ready |

**Decision Gate 1**: Assessment works end-to-end with 5+ test users.

## Sprint 2 (W3-W4): Adaptive Pathway & Micro-task Flow

**Goal**: Students can learn through adaptive pathway with real-time mastery tracking.

| Task | Priority | Acceptance Criteria |
|------|----------|-------------------|
| BKT engine | P0 | Mastery state updates correctly per concept |
| Adaptive pathway logic | P0 | Low/medium/high mastery triggers correct actions |
| Micro-task CRUD API | P0 | Tasks linked to milestones and concepts |
| Student pathway page | P0 | Shows concept map, current task, progress |
| Micro-task UI | P0 | Task view with goal, timer, submission |
| Task completion flow | P0 | Submit -> evaluate -> update mastery -> feedback |
| Retry with supplementary | P0 | Failed tasks show supplementary content |
| Wellbeing nudge | P1 | Nudge appears after 50 min, tracked |
| Student dashboard | P1 | Stats, mastery chart, pathway progress |
| Content intervention log | P1 | All system interventions logged |

**Decision Gate**: Adaptive flow tested with 10+ mock student journeys.

## Sprint 3 (W5-W6): Lecturer Dashboard & Event Pipeline

**Goal**: Lecturers can see early warnings and take actions.

| Task | Priority | Acceptance Criteria |
|------|----------|-------------------|
| Nightly batch analytics | P0 | Celery beat job runs successfully |
| Early warning engine | P0 | Inactivity, retry, milestone triggers computed |
| Alert generation (R/Y/G) | P0 | Alerts created with correct severity |
| Lecturer overview page | P0 | On-track/watch/urgent counts visible |
| Alert detail view | P0 | Student, reason, concept, suggested action shown |
| Quick action buttons | P0 | Send message, suggest task, schedule meeting |
| Intervention action log | P0 | All actions logged with follow-up status |
| Intervention history | P1 | Historical view of who, when, what, result |
| Data cleaning pipeline | P1 | Missing data handled, quality score computed |
| Dashboard performance | P1 | Load < 3 seconds with Redis caching |

**Decision Gate**: 2 lecturers confirm dashboard is "easy to understand" in review.

## Sprint 4 (W7-W8): UAT, Hardening & Launch Prep

**Goal**: System is stable, secure, and ready for pilot.

| Task | Priority | Acceptance Criteria |
|------|----------|-------------------|
| Unit tests (critical flows) | P0 | Assessment, BKT, pathway, alerts tested |
| Integration tests | P0 | End-to-end student/lecturer journeys pass |
| UAT with real users | P0 | 20-30 SV, 2 GV test and give feedback |
| Bug fixes from UAT | P0 | All P0 bugs resolved |
| Performance testing | P1 | 200 concurrent users, < 3s load |
| Security hardening | P0 | HTTPS, PII encryption, audit log |
| Pseudonymization | P1 | Analytics use anonymized data |
| Privacy consent flow | P0 | Students agree before data collection |
| Staging deployment | P0 | Staging env matches production |
| Monitoring setup | P1 | Sentry configured, health checks running |
| Launch checklist | P0 | All items verified |

**Decision Gate**: Launch checklist 100% complete.

## Sprint 5 (W9-W10): Pilot Run & Reporting

**Goal**: Live pilot running, data collected, KPIs measured.

| Task | Priority | Acceptance Criteria |
|------|----------|-------------------|
| Production deployment | P0 | System live and accessible |
| Student onboarding | P0 | All 60-90 students complete assessment |
| Daily monitoring | P0 | No critical incidents unresolved > 4 hours |
| KPI tracking | P0 | All 5 KPIs computed weekly |
| CSAT survey | P1 | Survey sent at end of sprint 3 and 5 |
| Week 4 report | P0 | Baseline data + readiness assessment |
| Week 10 report | P0 | Full KPI evaluation + lessons learned |
| Decision gate data | P0 | Go/no-go evidence package prepared |

## Post-Pilot (W11-W16)

| Week | Activity |
|------|----------|
| W11-W12 | Data analysis, lessons learned compilation |
| W13-W14 | Final report writing |
| W15 | Presentation to BGH |
| W16 | Decision Gate 3: Go/No-go for Phase 2 |

## RACI Matrix

| Activity | PO | Dev | GV | Phòng ĐT | BGH |
|----------|-----|-----|-----|----------|-----|
| Backlog & KPI | R/A | C | C | I | I |
| Sprint execution | A | R | I | I | I |
| Data access | R | C | I | A | A |
| Content review | C | I | R/A | I | I |
| UAT & launch | A | R | R | I | I |
| Pilot launch | R | R | R | A | A |
| Reports (W4/10/16) | R | C | C | I | A |
| Go/No-go decision | R | C | C | C | A |

R = Responsible, A = Accountable, C = Consulted, I = Informed

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Data too noisy | High | High | Cold start from assessment; pilot with min data |
| GV don't use dashboard | Medium | High | Action-oriented design, workshop, override |
| SV not engaged | Medium | Medium | UAT early, gentle nudges, no forced gamification |
| Privacy violation | Low | Very High | Pre-approved consent, audit log, access control |
| Scope creep | High | Medium | Locked MVP scope, PO gate for all changes |

## Success Criteria

Pilot is successful when ALL of these are met simultaneously:
1. Active learning time increased by >= 20%
2. Micro-task completion >= 70%
3. CSAT >= 4.0/5
4. GV dashboard usage >= 2x/week
5. No critical security/privacy incidents
