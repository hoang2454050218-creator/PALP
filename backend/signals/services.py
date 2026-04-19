"""
Ingest + rollup orchestration for behavioural signals.

The ingest endpoint accepts a batch of raw events from the frontend SDK,
emits them via ``events.emitter`` (single source of truth for the events
table), and updates the matching 5-minute ``SignalSession`` rollup row in
one ``transaction.atomic`` block. The whole pipeline is idempotent on
``(student, raw_session_id, window_start, idempotency_key)`` so the
client can safely retry on network errors.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone as tz
from typing import Iterable

from django.db import transaction
from django.utils import timezone

from events.emitter import emit_event
from events.models import EventLog
from events.schemas import SchemaValidationError

from .models import BehaviorScore, SignalSession, _floor_to_window_start
from .scoring import (
    compute_focus_minutes,
    compute_frustration_score,
    compute_idle_minutes,
    compute_session_quality,
)

logger = logging.getLogger("palp.events")

WINDOW_MINUTES = 5
WINDOW_SECONDS = WINDOW_MINUTES * 60

# Subset of the new EventName values that the ingest endpoint accepts.
# Anything else gets rejected at the serializer level so the endpoint
# can't be turned into a generic event drainer.
ACCEPTED_EVENT_NAMES = {
    EventLog.EventName.FOCUS_LOST,
    EventLog.EventName.FOCUS_GAINED,
    EventLog.EventName.TAB_SWITCHED,
    EventLog.EventName.IDLE_STARTED,
    EventLog.EventName.IDLE_ENDED,
    EventLog.EventName.SCROLL_DEPTH,
    EventLog.EventName.HINT_REQUESTED,
    EventLog.EventName.FRUSTRATION_SIGNAL,
    EventLog.EventName.GIVE_UP_SIGNAL,
    EventLog.EventName.RESPONSE_TIME_OUTLIER,
    EventLog.EventName.STRUGGLE_DETECTED,
}


@transaction.atomic
def ingest_events(
    *,
    student,
    raw_session_id: str,
    events: Iterable[dict],
    canonical_session_id: uuid.UUID | None = None,
) -> dict:
    """Persist a batch of behavioural events + update rollup.

    Returns a summary dict consumed by the API view + tests.

    Each ``event`` is ``{event_name, client_timestamp, properties, idempotency_key?}``.
    Invalid/unknown event_names are reported in the response and skipped
    rather than failing the whole batch (better UX for the SDK retry
    loop).
    """
    accepted = 0
    rejected: list[dict] = []
    duplicates = 0
    rollups_touched: set[int] = set()

    for raw in events:
        event_name = raw.get("event_name")
        if event_name not in ACCEPTED_EVENT_NAMES:
            rejected.append({"event_name": event_name, "reason": "not_accepted"})
            continue

        client_ts = _parse_timestamp(raw.get("client_timestamp"))
        if client_ts is None:
            rejected.append({"event_name": event_name, "reason": "bad_timestamp"})
            continue

        props = raw.get("properties") or {}
        try:
            event = emit_event(
                event_name,
                actor=student,
                actor_type=EventLog.ActorType.STUDENT,
                session_id=raw_session_id,
                client_timestamp=client_ts,
                properties=props,
                idempotency_key=raw.get("idempotency_key"),
            )
        except SchemaValidationError as exc:
            rejected.append({"event_name": event_name, "reason": str(exc)})
            continue

        if event is None:
            rejected.append({"event_name": event_name, "reason": "ingest_failed"})
            continue

        if event.confirmed_at is not None and event.created_at != event.confirmed_at:
            # Existing dedup'd row — treat as duplicate, no rollup update.
            duplicates += 1
            continue

        rollup = _update_rollup(
            student=student,
            raw_session_id=raw_session_id,
            canonical_session_id=canonical_session_id,
            client_timestamp=client_ts,
            event_name=event_name,
            properties=props,
        )
        rollups_touched.add(rollup.pk)
        accepted += 1

    return {
        "accepted": accepted,
        "rejected": rejected,
        "duplicates": duplicates,
        "rollups_touched": len(rollups_touched),
    }


def _parse_timestamp(raw) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=tz.utc)
    if isinstance(raw, str):
        # Handle "Z" suffix that JSON.stringify produces
        cleaned = raw.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(cleaned)
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=tz.utc)
    if isinstance(raw, (int, float)):
        return datetime.fromtimestamp(raw / 1000.0, tz=tz.utc)
    return None


def _update_rollup(
    *,
    student,
    raw_session_id: str,
    canonical_session_id: uuid.UUID | None,
    client_timestamp: datetime,
    event_name: str,
    properties: dict,
) -> SignalSession:
    window_start = _floor_to_window_start(client_timestamp, minutes=WINDOW_MINUTES)
    window_end = window_start + timedelta(minutes=WINDOW_MINUTES)

    rollup, _created = SignalSession.objects.get_or_create(
        student=student,
        raw_session_id=raw_session_id,
        window_start=window_start,
        defaults={
            "canonical_session_id": canonical_session_id,
            "window_end": window_end,
            "last_event_at": client_timestamp,
        },
    )

    # Late-arriving canonical id wins
    if canonical_session_id and not rollup.canonical_session_id:
        rollup.canonical_session_id = canonical_session_id

    if event_name == EventLog.EventName.FOCUS_LOST:
        away_ms = max(0, int(properties.get("focus_duration_ms", 0)))
        rollup.idle_minutes = round(rollup.idle_minutes + away_ms / 60_000.0, 3)
    elif event_name == EventLog.EventName.IDLE_STARTED:
        idle_ms = max(0, int(properties.get("idle_duration_ms", 0)))
        rollup.idle_minutes = round(rollup.idle_minutes + idle_ms / 60_000.0, 3)
    elif event_name == EventLog.EventName.IDLE_ENDED:
        idle_ms = max(0, int(properties.get("idle_duration_ms", 0)))
        rollup.idle_minutes = round(rollup.idle_minutes + idle_ms / 60_000.0, 3)
    elif event_name == EventLog.EventName.FOCUS_GAINED:
        # Implicitly contributes to focus minutes (away ended); we just
        # cap idle at the window length to avoid overcounting.
        rollup.idle_minutes = min(rollup.idle_minutes, float(WINDOW_MINUTES))
    elif event_name == EventLog.EventName.TAB_SWITCHED:
        rollup.tab_switches = (rollup.tab_switches or 0) + 1
    elif event_name == EventLog.EventName.HINT_REQUESTED:
        rollup.hint_count = (rollup.hint_count or 0) + 1
    elif event_name == EventLog.EventName.FRUSTRATION_SIGNAL:
        intensity = max(0.0, min(1.0, float(properties.get("intensity", 0.5))))
        rollup.frustration_score = max(rollup.frustration_score, intensity)
    elif event_name == EventLog.EventName.GIVE_UP_SIGNAL:
        rollup.give_up_count = (rollup.give_up_count or 0) + 1
    elif event_name == EventLog.EventName.RESPONSE_TIME_OUTLIER:
        rollup.response_time_outliers = (rollup.response_time_outliers or 0) + 1
    elif event_name == EventLog.EventName.STRUGGLE_DETECTED:
        rollup.struggle_count = (rollup.struggle_count or 0) + 1

    # Compute focus minutes as window length minus idle (clamped).
    rollup.focus_minutes = round(
        max(0.0, float(WINDOW_MINUTES) - rollup.idle_minutes), 3
    )
    rollup.raw_event_count = (rollup.raw_event_count or 0) + 1
    rollup.last_event_at = client_timestamp
    rollup.save()
    return rollup


def rollup_day(student, day) -> BehaviorScore:
    """Aggregate every SignalSession of ``student`` on ``day`` into BehaviorScore."""
    start = timezone.make_aware(datetime.combine(day, datetime.min.time())) if not isinstance(day, datetime) else day
    end = start + timedelta(days=1)
    rows = list(
        SignalSession.objects.filter(
            student=student,
            window_start__gte=start,
            window_start__lt=end,
        )
    )
    score, _ = BehaviorScore.objects.update_or_create(
        student=student,
        day=start.date(),
        defaults={
            "total_focus_minutes": round(sum(r.focus_minutes for r in rows), 3),
            "total_idle_minutes": round(sum(r.idle_minutes for r in rows), 3),
            "avg_focus_score": round(
                sum(r.session_quality for r in rows) / len(rows), 4
            ) if rows else 0.0,
            "avg_frustration_score": round(
                sum(r.frustration_score for r in rows) / len(rows), 4
            ) if rows else 0.0,
            "total_tab_switches": sum(r.tab_switches for r in rows),
            "total_give_up_count": sum(r.give_up_count for r in rows),
            "total_struggle_count": sum(r.struggle_count for r in rows),
            "total_hint_count": sum(r.hint_count for r in rows),
            "sessions_count": len(rows),
        },
    )
    return score


__all__ = [
    "WINDOW_MINUTES",
    "ACCEPTED_EVENT_NAMES",
    "ingest_events",
    "rollup_day",
    "compute_focus_minutes",
    "compute_idle_minutes",
    "compute_frustration_score",
    "compute_session_quality",
]
