---
name: celery-task
description: Idempotent, retryable, observable Celery task pattern for PALP. Use when adding any task under backend/<app>/tasks.py or scheduling Celery beat jobs.
---

# Celery Task — Idempotent + Retryable Pattern

## When to use

- Adding a new task to `backend/<app>/tasks.py`
- Scheduling a job via Celery beat
- Refactoring a long-running view into background processing
- Debugging task retry storms or duplicate execution

## Canonical task template

```python
import logging
from celery import shared_task
from django.db import transaction

logger = logging.getLogger("palp.celery")


@shared_task(
    bind=True,
    name="adaptive.tasks.recompute_mastery",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=3,
    soft_time_limit=240,
    time_limit=300,
    acks_late=True,
)
def recompute_mastery(self, student_id: int, concept_id: int) -> dict:
    """Recompute BKT mastery for one (student, concept). Idempotent."""
    logger.info(
        "Recomputing mastery",
        extra={"student_id": student_id, "concept_id": concept_id, "task_id": self.request.id},
    )

    with transaction.atomic():
        state = MasteryState.objects.select_for_update().get(
            student_id=student_id, concept_id=concept_id
        )
        events = SubmissionEvent.objects.filter(
            student_id=student_id, concept_id=concept_id, processed=False
        ).order_by("created_at")

        new_p = state.mastery_p
        for event in events:
            new_p = update_mastery(new_p, event.is_correct)
            event.processed = True

        state.mastery_p = round(new_p, 4)
        state.save(update_fields=["mastery_p", "updated_at"])
        SubmissionEvent.objects.bulk_update(events, ["processed"])

    logger.info(
        "Mastery recomputed",
        extra={
            "student_id": student_id,
            "concept_id": concept_id,
            "new_mastery_p": state.mastery_p,
            "events_processed": len(events),
        },
    )
    return {"student_id": student_id, "concept_id": concept_id, "mastery_p": state.mastery_p}
```

## Hard rules

### Idempotency

- Re-running the same task with the same args produces the same outcome.
- Use a "processed" flag, version counter, or upsert pattern. Never blindly increment.
- Wrap multi-step writes in `transaction.atomic()` with `select_for_update()` to avoid races.
- For external side-effects (email, webhook), use a Sent table to dedupe by message_id.

### Retry policy

- `autoretry_for=(Exception,)` — retry on any exception. Override to a tuple of specific exceptions if you have non-retryable errors (`PermissionDenied`, `ValidationError`).
- `retry_backoff=True` + `retry_backoff_max=600` — exponential backoff capped at 10 min.
- `retry_jitter=True` — avoid thundering herd.
- `max_retries=3` — fail to dead-letter after 3 attempts (default for PALP).
- `acks_late=True` — only ack after task succeeds; if worker dies mid-task, broker re-delivers.

### Time limits

- `soft_time_limit=240` (4 min) — raises `SoftTimeLimitExceeded`, allows cleanup.
- `time_limit=300` (5 min) — hard kill. Set per-task if longer is needed (e.g. ETL: 1800/3600).
- Long-running ETL jobs should chunk (process 1000 rows per task, queue next chunk).

### Naming

- `name="<app>.tasks.<task_name>"` explicit — survives module rename.
- Snake_case verb: `recompute_mastery`, `send_intervention`, `enforce_retention`.

### Logging

- Logger: `palp.celery`
- Always include `extra={"task_id": self.request.id, ...domain_ids}` for tracing.
- Log start AND completion (or failure). Use `info` for normal, `warning` for retry, `error` for permanent failure.

### Observability

- Tasks auto-export Prometheus metrics via `django-prometheus` + Celery integration.
- Critical tasks should emit `EventLog` via `events.services.audit_log` so they show up in analytics.
- Add Grafana panel for task duration P95 + failure rate per task name.

## Beat schedule

`backend/palp/celery.py`:

```python
app.conf.beat_schedule = {
    "nightly-analytics": {
        "task": "analytics.tasks.run_nightly_analytics",
        "schedule": crontab(hour=2, minute=0),
    },
    "enforce-retention": {
        "task": "privacy.tasks.enforce_retention",
        "schedule": crontab(hour=3, minute=0),
    },
    "early-warning-scan": {
        "task": "dashboard.tasks.scan_early_warnings",
        "schedule": crontab(minute="*/15"),
    },
}
```

Use `crontab()` not raw seconds. Document timezone (Asia/Ho_Chi_Minh) explicitly when ambiguous.

## Testing

```python
@pytest.mark.django_db
class TestRecomputeMastery:
    def test_happy_path(self, student, concept, submission_events):
        result = recompute_mastery(student.id, concept.id)
        assert result["mastery_p"] >= 0
        assert result["mastery_p"] <= 1

    def test_idempotent(self, student, concept, submission_events):
        first = recompute_mastery(student.id, concept.id)
        second = recompute_mastery(student.id, concept.id)
        assert first == second

    def test_retries_on_db_error(self, monkeypatch):
        # Patch select_for_update to raise once, ensure retry
        ...
```

In test settings (`palp.settings.test`), `CELERY_TASK_ALWAYS_EAGER=True` runs tasks synchronously — no broker needed.

## Anti-patterns (forbidden)

- `@shared_task` without `name=` — module rename breaks the queue.
- Mutating shared state outside the DB transaction.
- Long-running tasks without checkpointing (chunking).
- Catching all exceptions and returning success — hide the failure, lose the retry.
- Using `time.sleep()` to wait for external services — use `self.retry(countdown=...)`.
- Tasks that write to the file system (use S3 or DB BLOB).
- Tasks that import `request`/`HttpResponse` — Celery has no HTTP context.
