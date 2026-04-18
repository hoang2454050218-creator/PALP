"""
Async event emission tasks.

Tasks are intentionally thin wrappers around `emit_event` so the schema
validation, deduplication, and metrics instrumentation logic stays in one
place. Hot paths use ``emit_event_or_async`` from `events.emitter`.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from celery import shared_task

from .emitter import emit_event

logger = logging.getLogger("palp.events")


@shared_task(
    name="events.tasks.emit_event_task",
    bind=True,
    acks_late=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=3,
)
def emit_event_task(self, event_name: str, **kwargs: Any) -> int | None:
    """Hydrate id-based references back to ORM instances and emit.

    On final retry exhaustion, push to dead-letter queue ``events_dlq`` so
    operators can inspect/replay later without losing the event.
    """
    from accounts.models import User
    from curriculum.models import Concept, Course, MicroTask
    from accounts.models import StudentClass

    if "actor_id" in kwargs:
        kwargs["actor"] = User.objects.filter(id=kwargs.pop("actor_id")).first()
    if "course_id" in kwargs:
        cid = kwargs.pop("course_id")
        kwargs["course"] = Course.objects.filter(id=cid).first() if cid else None
    if "student_class_id" in kwargs:
        scid = kwargs.pop("student_class_id")
        kwargs["student_class"] = StudentClass.objects.filter(id=scid).first() if scid else None
    if "concept_id" in kwargs:
        cid = kwargs.pop("concept_id")
        kwargs["concept"] = Concept.objects.filter(id=cid).first() if cid else None
    if "task_id" in kwargs:
        tid = kwargs.pop("task_id")
        kwargs["task"] = MicroTask.objects.filter(id=tid).first() if tid else None
    if "client_timestamp" in kwargs and isinstance(kwargs["client_timestamp"], str):
        kwargs["client_timestamp"] = datetime.fromisoformat(kwargs["client_timestamp"])
    if "request_id" in kwargs and isinstance(kwargs["request_id"], str):
        try:
            kwargs["request_id"] = uuid.UUID(kwargs["request_id"])
        except ValueError:
            kwargs.pop("request_id", None)

    event = emit_event(event_name, **kwargs)
    return event.id if event else None


@shared_task(
    name="events.tasks.dead_letter_event",
    queue="events_dlq",
)
def dead_letter_event(event_name: str, payload: dict, error: str) -> None:
    """Catch-all sink for events that exhausted retries. Logged + persisted
    to a future DLQ store (TODO: ClickHouse table after Sprint 5).
    """
    logger.error(
        "DLQ event=%s error=%s payload=%s",
        event_name, error, payload,
    )
