# Architecture Decision Records (ADR)

Repository of significant architectural decisions for PALP, written in the
[MADR](https://adr.github.io/madr/) format.

## Index

| # | Title | Status | Date |
|---|-------|--------|------|
| [001](001-jwt-cookie-httponly.md) | JWT in httpOnly cookie thay vì Authorization header | Accepted | 2026-04 |
| [002](002-bkt-vs-dkt.md) | Bayesian Knowledge Tracing thay vì Deep Knowledge Tracing | Accepted | 2026-04 |
| [003](003-celery-vs-kafka.md) | Celery + Redis thay vì Kafka cho event pipeline | Accepted | 2026-04 |
| [004](004-fernet-vs-pgcrypto.md) | Fernet field-level encryption thay vì pgcrypto | Accepted | 2026-04 |
| [005](005-compose-pilot-k8s-phase2.md) | docker-compose cho pilot, K8s cho phase 2 | Accepted | 2026-04 |
| [006](006-nextjs-app-router.md) | Next.js 14 App Router + standalone output | Accepted | 2026-04 |
| [007](007-spectacular-oasdiff.md) | drf-spectacular + oasdiff thay vì manual OpenAPI | Accepted | 2026-04 |
| [008](008-pgbouncer-transaction-pool.md) | PgBouncer transaction pooling cho production | Accepted | 2026-04 |

## Process

1. Mọi quyết định ảnh hưởng kiến trúc (>2 file, >1 module) phải có ADR.
2. ADR submit qua PR với 1 reviewer architect + 1 reviewer tech-lead.
3. Status workflow: `Proposed` → `Accepted` | `Rejected` | `Superseded by ADR-XXX`.
4. Không sửa ADR đã `Accepted`, viết ADR mới tham chiếu lại.
