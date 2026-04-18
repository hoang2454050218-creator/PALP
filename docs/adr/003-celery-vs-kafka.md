# ADR-003: Celery + Redis thay vì Kafka cho event pipeline

* Status: Accepted
* Date: 2026-04
* Deciders: Tech Lead, Platform Lead
* Tags: infrastructure, event-driven, scalability

## Context

PALP có 4 loại workload async:
1. Event ingestion từ frontend (`/api/events/track/` + `/batch/`).
2. Nightly early warning per class.
3. Weekly KPI report.
4. Periodic data quality + audit tasks.

Pilot scale: 60-90 students × ~50 events/day = ~5K events/day = 0.06 ev/s.
Phase 2 target: 5 trường × 500 students = ~125K events/day = 1.4 ev/s.

## Decision

Dùng **Celery 5.4 + Redis 7** broker + result backend cho cả pilot và
phase 2 (đến ~10 ev/s). Đánh giá lại với Kafka khi >50 ev/s hoặc cần
exactly-once semantic.

Setup:
* Broker DB Redis `1`, result DB `2`, cache DB `0`, ratelimit DB `3`.
* Queue: `celery` (default), `events_high` (priority 9 cho event emission),
  `events_dlq` (dead letter).
* `acks_late=True` + `max_retries=3` cho task quan trọng.
* `task_time_limit=300s`, `task_soft_time_limit=240s`.

## Consequences

### Positive

* Đơn giản: 1 Redis container thay vì Kafka cluster (Zookeeper/KRaft).
* Native Django integration (`django-celery-beat` cho scheduler trong DB).
* Đủ throughput cho pilot và phase 2 đến ~5 trường.
* Operations team đã quen Redis hơn Kafka.

### Negative

* Không có exactly-once semantic (mitigation: idempotency_key trong EventLog).
* Không có log compaction cho event sourcing (PALP chưa cần event sourcing).
* Single point of failure cho Redis (mitigation: Redis Sentinel cho HA
  trong phase 2, snapshot AOF trong dev).

## Alternatives considered

* **Kafka + Confluent Schema Registry**: over-engineered cho pilot, vận
  hành phức tạp, đội nhỏ không kham nổi.
* **AWS SQS + EventBridge**: vendor lock-in, chi phí khó dự đoán cho
  university budget Việt Nam.
* **NATS JetStream**: hứa hẹn nhưng community Python nhỏ, ít resource.

## References

* `backend/palp/celery.py`
* `backend/palp/settings/base.py` `CELERY_*` settings
* `backend/events/emitter.py` idempotency check
