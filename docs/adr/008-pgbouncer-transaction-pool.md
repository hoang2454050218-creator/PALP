# ADR-008: PgBouncer transaction pooling cho production

* Status: Accepted
* Date: 2026-04
* Deciders: Platform Lead, DBA
* Tags: database, performance, scalability

## Context

PALP production có:
* 1 Gunicorn (4 worker × 2 thread) = 8 connection slot.
* Celery worker (4 concurrency) = 4 connection slot.
* Celery beat = 1 connection slot.
* Total ~13 active connection.

Postgres mặc định `max_connections=100`. Có vẻ thừa cho pilot, nhưng:
* Phase 2 với 5 backend instance = 65 connection.
* Mỗi connection ~10MB RAM → 650MB chỉ cho idle connections.
* Connection establishment overhead 5-10ms mỗi request lạnh.

## Decision

Triển khai **PgBouncer** trong production compose (`edoburu/pgbouncer`):
* Mode `transaction` (release connection sau mỗi transaction).
* `default_pool_size=25`, `max_client_conn=200`.
* Backend `DATABASES['default']['HOST']=pgbouncer`, port 5432.
* Pilot tạm bypass cho dev compose (overhead không đáng).

## Consequences

### Positive

* Connection reuse → giảm latency 5-10ms p99.
* Backend instance scale ngang không bùng connection.
* Postgres backend memory ổn định ~250MB thay vì leo theo backend instance.

### Negative

* Transaction mode không support `LISTEN/NOTIFY`, prepared statements with
  `psycopg2` (nếu có). PALP không dùng → OK.
* Một layer thêm: debugging connection issue cần check PgBouncer log.
* Mitigation: PgBouncer health check trong compose + log structured.

## Alternatives considered

* **Session pooling**: ít restriction nhưng connection reuse ít hiệu quả.
* **App-level pooling (Django CONN_MAX_AGE=600)**: đã dùng, nhưng chỉ
  reuse trong worker process, không cross-worker.
* **AWS RDS Proxy / Google Cloud SQL Auth Proxy**: vendor lock-in.

## References

* `docker-compose.prod.yml` `pgbouncer` service (Sprint 3)
* `backend/palp/settings/production.py` `DATABASES`
