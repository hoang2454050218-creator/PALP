# PALP - Architecture Decision Record

## System Architecture

```
┌─────────────────────────────────────────────────┐
│                   Client Layer                   │
│  ┌──────────┐  ┌──────────────┐  ┌───────────┐  │
│  │ Student  │  │   Lecturer   │  │   Admin   │  │
│  │  Portal  │  │  Dashboard   │  │   Panel   │  │
│  └────┬─────┘  └──────┬───────┘  └─────┬─────┘  │
│       │               │               │         │
│       └───────────────┼───────────────┘         │
│                Next.js 14 (App Router)           │
└────────────────────────┬────────────────────────┘
                         │ HTTPS / JWT
┌────────────────────────┼────────────────────────┐
│                  API Layer                       │
│            Django REST Framework                 │
│  ┌──────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │ Auth │ │Assessment│ │ Adaptive │ │  Dash  │ │
│  │ RBAC │ │  Engine  │ │  Engine  │ │ board  │ │
│  └──────┘ └──────────┘ └──────────┘ └────────┘ │
│  ┌──────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │Events│ │Curriculum│ │Analytics │ │Wellbein│ │
│  └──────┘ └──────────┘ └──────────┘ └────────┘ │
└────────────┬──────────────────┬─────────────────┘
             │                  │
┌────────────┼──────────────────┼─────────────────┐
│     ┌──────┴──────┐    ┌──────┴──────┐          │
│     │ PostgreSQL  │    │    Redis    │          │
│     │   16        │    │    7        │          │
│     └─────────────┘    └─────────────┘          │
│                  Data Layer                      │
└─────────────────────────────────────────────────┘
             │
┌────────────┼────────────────────────────────────┐
│     ┌──────┴──────┐                              │
│     │   Celery    │  Nightly batch:              │
│     │   Workers   │  - Early warning computation │
│     │   + Beat    │  - Analytics aggregation     │
│     └─────────────┘  - Data quality checks       │
│              Background Jobs                     │
└─────────────────────────────────────────────────┘
```

## Adaptive Engine Design

### Bayesian Knowledge Tracing (BKT)

BKT models knowledge as a latent binary variable per concept per student.

**Parameters** (per concept):
- `P(L0) = 0.30` - prior probability of mastery
- `P(T) = 0.09` - probability of learning on each opportunity
- `P(G) = 0.25` - probability of correct guess when unmastered
- `P(S) = 0.10` - probability of slip when mastered

**Update Algorithm**:

On correct answer:
```
P(L|correct) = P(L) * (1-P(S)) / [P(L)*(1-P(S)) + (1-P(L))*P(G)]
P(L_new) = P(L|correct) + (1 - P(L|correct)) * P(T)
```

On incorrect answer:
```
P(L|wrong) = P(L) * P(S) / [P(L)*P(S) + (1-P(L))*(1-P(G))]
P(L_new) = P(L|wrong) + (1 - P(L|wrong)) * P(T)
```

### Pathway Decision Rules

| Condition | Action | Difficulty Adj |
|-----------|--------|---------------|
| P(mastery) < 0.60 | Insert supplementary content | -1 |
| 0.60 <= P(mastery) <= 0.85 | Continue current path | 0 |
| P(mastery) > 0.85 | Advance to next concept | +1 |

### Caching Strategy

- MasteryState cached in Redis with 5-minute TTL
- Cache key: `mastery:{student_id}:{concept_id}`
- Cache invalidated on each BKT update
- Dashboard data cached with 1-minute TTL for hot queries

## Early Warning System

### Trigger Classification

```
                    ┌─────────────────┐
                    │  Student Events  │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │  Nightly Batch  │
                    │  (Celery Beat)  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────┴───┐  ┌──────┴─────┐ ┌──────┴──────┐
     │ Inactivity │  │   Retry    │ │  Milestone  │
     │   Check    │  │  Failures  │ │    Lag      │
     └────────┬───┘  └──────┬─────┘ └──────┬──────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                    ┌────────┴────────┐
                    │ Alert Generator │
                    │ (Severity:     │
                    │ Red/Yellow)    │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │   Dashboard    │
                    │   Display     │
                    └───────────────┘
```

### Severity Rules

- **RED**: Inactivity >= 5 days OR retry failures >= 3 on same concept
- **YELLOW**: Inactivity 3-4 days OR milestone progress significantly behind peers
- **GREEN**: Normal engagement (no alert generated)

## Technology Decisions

### Why Django over FastAPI?

- Mature ORM with migration support
- Built-in admin panel for rapid data management
- SimpleJWT for authentication
- Django Celery Beat for scheduled tasks
- Stronger ecosystem for the team's experience level

### Why Next.js App Router?

- Server-side rendering for SEO (future)
- File-based routing matches our page structure
- React Server Components for dashboard performance
- Built-in API route proxying to Django backend

### Why PostgreSQL + Redis (not MongoDB, etc.)?

- PostgreSQL: ACID compliance for student data, strong JSON support
- Redis: Lightweight caching for mastery states and dashboard queries
- Both are proven, well-documented, and easy to operate

### Why Celery (not real-time streaming)?

- Pilot scale (60-90 students) doesn't warrant Kafka
- Nightly batch is sufficient for early warning computation
- Simpler operational burden for a small team
- Can migrate to real-time in Phase 2 if needed

## Security Architecture

### Authentication Flow

```
Client -> POST /api/auth/login/ (username, password)
       <- JWT {access_token, refresh_token}

Client -> GET /api/... (Authorization: Bearer <access_token>)
       <- 200 OK (data)

Client -> POST /api/auth/token/refresh/ (refresh_token)
       <- JWT {new_access_token, new_refresh_token}
```

### RBAC Matrix

| Resource | Student | Lecturer | Admin |
|----------|---------|----------|-------|
| Own assessment | RW | R | RW |
| Own mastery | R | - | R |
| Own pathway | RW | - | R |
| Class students | - | R | RW |
| Dashboard alerts | - | RW | RW |
| Interventions | - | RW | RW |
| Analytics/KPI | - | R | RW |
| User management | - | - | RW |

### Data Protection

- PII encrypted at rest (AES-256 via Django field encryption)
- TLS 1.3 for all API communication
- Analytics run on pseudonymized data only
- Lecturers see only their assigned class students
- Audit log for all data access operations
