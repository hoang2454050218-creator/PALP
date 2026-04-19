---
name: event-taxonomy
description: Learning-analytics event taxonomy for backend/events. Use when emitting EventLog entries, adding a new event_name, or building dashboards/queries on events.
---

# Event Taxonomy — Learning Analytics

## When to use

- Calling `events.services.audit_log(...)` or `EventLog.objects.create(...)`
- Adding a new event_name (requires migration)
- Building dashboards on `EventLog` data
- Interpreting analytics ETL output (`scripts/etl_academic.py`)

## Canonical event_name choices

Source: `backend/events/migrations/0007_alter_eventlog_event_name.py` (current taxonomy).

### Session lifecycle

| event_name | Khi nào emit | Actor |
|------------|--------------|-------|
| `session_started` | User log in / first request after >30min idle | student / lecturer |
| `session_ended` | User log out hoặc session timeout | student / lecturer |

### Assessment

| event_name | Khi nào emit | Actor |
|------------|--------------|-------|
| `assess_answer` | Submit answer cho 1 question | student |
| `assess_complete` | Nộp toàn bộ assessment | student |
| `assess_expired` | Hết giờ assessment | system |
| `assess_resumed` | Tiếp tục assessment đang dở | student |
| `assessment_completed` | Sau khi grading xong | system |

### Learning loop

| event_name | Khi nào emit | Actor |
|------------|--------------|-------|
| `micro_task_completed` | Hoàn thành 1 micro-task | student |
| `content_intervention` | Hệ thống chèn supplementary content | system |
| `retry_triggered` | Retry policy fired (mastery thấp) | system |

### Lecturer / dashboard

| event_name | Khi nào emit | Actor |
|------------|--------------|-------|
| `gv_dashboard_viewed` | GV mở dashboard | lecturer |
| `gv_action_taken` | GV thực hiện can thiệp (gửi nudge, tạo intervention) | lecturer |
| `alert_dismissed` | GV bỏ qua early-warning alert | lecturer |
| `intervention_created` | Intervention record được tạo | lecturer / system |

### Wellbeing

| event_name | Khi nào emit | Actor |
|------------|--------------|-------|
| `wellbeing_nudge` | Nudge engine quyết định nhắc | system |
| `wellbeing_nudge_shown` | UI render nudge cho user | system |
| `wellbeing_nudge_accepted` | User click "Đi nghỉ" | student |
| `wellbeing_nudge_dismissed` | User dismiss nudge | student |

### Telemetry

| event_name | Khi nào emit | Actor |
|------------|--------------|-------|
| `page_view` | Frontend navigation event | student / lecturer |

### ETL

| event_name | Khi nào emit | Actor |
|------------|--------------|-------|
| `etl_started` | `scripts/etl_academic.py` start | system |
| `etl_completed` | ETL finish OK | system |
| `etl_failed` | ETL exception | system |

## How to emit (canonical)

```python
from events.services import audit_log

audit_log(
    event_name="micro_task_completed",
    actor=request.user,
    target=micro_task,
    payload={"score": 0.87, "duration_s": 145},
    request=request,
)
```

`audit_log` validates `event_name` against the choices above. Invalid name raises `ValidationError`.

## Adding a new event_name

1. Discuss in issue + ADR if it's a core flow
2. Edit `backend/events/models.py::EventLog.EVENT_CHOICES`
3. Run `python manage.py makemigrations events`
4. Add Vietnamese label `("new_event", "Mô tả tiếng Việt")`
5. Update this skill doc with the new row
6. Add unit test in `backend/events/tests/`
7. Update `docs/DATA_MODEL.md` if event affects analytics schema
8. Notify analytics team — dashboards may need new query

## Hard rules

- Never emit PII in `payload` field — use IDs only, resolve PII at query time with consent + RBAC.
- Always include `request` so middleware fills `request_id`, `ip_hash`, `user_agent`.
- `actor` may be `None` for system-generated events (`etl_*`, `wellbeing_nudge` triggered by Celery).
- Idempotency: same event emitted twice should be detectable via `request_id` + `event_name` + actor.

## Querying

```python
EventLog.objects.filter(
    event_name="assess_complete",
    timestamp__gte=since,
    actor=student,
).select_related("actor")
```

Index: `palp_event_actor_ts_desc` on `(actor_id, timestamp DESC)` (migration 0006). Use it.
