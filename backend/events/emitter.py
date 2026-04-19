"""
Canonical event emission helper.

All event creation -- from API views, Celery tasks, and domain services --
should flow through `emit_event()` (sync) or `emit_event_async()` (Celery
task) to guarantee schema compliance, deduplication, and metrics
instrumentation.

Async path is preferred on hot request paths (SubmitTaskAttempt, login)
to drop ~80-150ms p95 by moving DB write off the request thread.
"""
import logging
import uuid
from datetime import datetime, timezone as tz

from django.conf import settings
from django.db import IntegrityError
from django.utils import timezone

from .models import EventLog
from .schemas import SchemaValidationError, validate_properties

logger = logging.getLogger("palp.events")

CLOCK_SKEW_MAX_SECONDS = 300


def emit_event(
    event_name: str,
    *,
    actor=None,
    actor_type: str = "",
    session_id: str = "",
    course=None,
    student_class=None,
    device_type: str = "",
    source_page: str = "",
    request_id: uuid.UUID | None = None,
    idempotency_key: str | None = None,
    client_timestamp: datetime | None = None,
    concept=None,
    task=None,
    difficulty_level: int | None = None,
    attempt_number: int | None = None,
    mastery_before: float | None = None,
    mastery_after: float | None = None,
    intervention_reason: str = "",
    properties: dict | None = None,
    confirmed: bool = False,
) -> EventLog | None:
    """
    Create a validated EventLog record.

    Returns the created EventLog, or the existing one if the
    idempotency_key already exists. Returns None only on unexpected error.
    """
    from events.metrics import EVENT_INGESTION_TOTAL

    now = timezone.now()
    ts_utc = now.astimezone(tz.utc).replace(tzinfo=tz.utc)

    if not actor_type and actor:
        actor_type = _resolve_actor_type(actor)
    if not actor_type:
        actor_type = EventLog.ActorType.SYSTEM

    clock_skew_detected = False
    if client_timestamp:
        delta = abs((ts_utc - client_timestamp).total_seconds())
        if delta > CLOCK_SKEW_MAX_SECONDS:
            clock_skew_detected = True

    event_properties = dict(properties or {})
    if clock_skew_detected:
        event_properties["clock_skew_detected"] = True
        event_properties["clock_skew_seconds"] = round(
            (ts_utc - client_timestamp).total_seconds(), 1
        )

    # Schema validation for events that have a registered contract.
    # Schemaless events (legacy or freeform) pass through unchanged.
    try:
        validate_properties(event_name, event_properties)
    except SchemaValidationError as exc:
        EVENT_INGESTION_TOTAL.labels(
            event_name=event_name, status="schema_invalid"
        ).inc()
        logger.warning("Rejecting event %s: %s", event_name, exc)
        raise

    if idempotency_key:
        existing = EventLog.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            EVENT_INGESTION_TOTAL.labels(
                event_name=event_name, status="deduplicated"
            ).inc()
            return existing

    course_id = _extract_id(course)
    class_id = _extract_id(student_class)
    concept_id = _extract_id(concept)
    task_id = _extract_id(task)

    try:
        event = EventLog.objects.create(
            event_name=event_name,
            event_version=EventLog.CURRENT_VERSION,
            timestamp_utc=ts_utc,
            client_timestamp=client_timestamp,
            actor_type=actor_type,
            actor=actor,
            session_id=session_id,
            course_id=course_id,
            student_class_id=class_id,
            device_type=device_type,
            source_page=source_page,
            request_id=request_id or uuid.uuid4(),
            idempotency_key=idempotency_key,
            concept_id=concept_id,
            task_id=task_id,
            difficulty_level=difficulty_level,
            attempt_number=attempt_number,
            mastery_before=mastery_before,
            mastery_after=mastery_after,
            intervention_reason=intervention_reason,
            confirmed_at=ts_utc if confirmed else None,
            properties=event_properties,
        )
        EVENT_INGESTION_TOTAL.labels(
            event_name=event_name, status="created"
        ).inc()
        return event

    except IntegrityError:
        existing = EventLog.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            EVENT_INGESTION_TOTAL.labels(
                event_name=event_name, status="deduplicated"
            ).inc()
            return existing

        logger.exception("Failed to create event %s", event_name)
        EVENT_INGESTION_TOTAL.labels(
            event_name=event_name, status="error"
        ).inc()
        return None


def confirm_event(event: EventLog) -> None:
    if event.confirmed_at is None:
        event.confirmed_at = timezone.now()
        event.save(update_fields=["confirmed_at"])


def emit_event_or_async(*args, use_async: bool | None = None, **kwargs):
    """Emit synchronously or via Celery depending on settings/override.

    Hot paths (`SubmitTaskAttempt`, login, page_view) should call this with
    ``use_async=True`` to push the DB write off the request thread. Falls
    back to sync emission if Celery is not configured (keeps unit tests
    green without a worker running).
    """
    if use_async is None:
        use_async = getattr(settings, "PALP_ASYNC_EVENTS", False)

    if not use_async:
        return emit_event(*args, **kwargs)

    try:
        from .tasks import emit_event_task

        # Convert ORM objects to ids so they survive JSON serialisation
        # to the broker. Datetime/UUID handled by Celery's JSON encoder.
        payload = dict(kwargs)
        for k in ("course", "student_class", "concept", "task", "actor"):
            obj = payload.pop(k, None)
            if obj is not None:
                payload[f"{k}_id"] = getattr(obj, "id", obj)
        if "client_timestamp" in payload and payload["client_timestamp"] is not None:
            ts = payload["client_timestamp"]
            payload["client_timestamp"] = ts.isoformat() if hasattr(ts, "isoformat") else ts
        if "request_id" in payload and payload["request_id"] is not None:
            payload["request_id"] = str(payload["request_id"])
        emit_event_task.apply_async(args=args, kwargs=payload, queue="events_high")
        return None
    except Exception:
        logger.exception("Async event emission failed; falling back to sync")
        return emit_event(*args, **kwargs)


def _resolve_actor_type(user) -> str:
    role_map = {
        "student": EventLog.ActorType.STUDENT,
        "lecturer": EventLog.ActorType.LECTURER,
        "admin": EventLog.ActorType.ADMIN,
    }
    return role_map.get(getattr(user, "role", ""), EventLog.ActorType.SYSTEM)


def _extract_id(obj):
    if obj is None:
        return None
    if isinstance(obj, int):
        return obj
    return getattr(obj, "id", obj)
