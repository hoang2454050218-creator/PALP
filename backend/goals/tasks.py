"""
Celery tasks for the Direction Engine.

* ``detect_drift_periodic`` — every 6 hours, evaluates every active
  WeeklyGoal and updates ``drift_pct_last_check`` + emits ``goal_drift``
  events when needed.
* ``open_weekly_reflections`` — Saturday 18:00 ICT (per
  ``CELERY_BEAT_SCHEDULE``), opens reflection stubs so the frontend can
  surface the journal prompt the moment the student logs in next.
"""
from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

from .drift_detector import detect_drift_for_active_goals
from .reflection import open_reflections_for_week
from .services import monday_of

logger = logging.getLogger("palp")


@shared_task(name="goals.detect_drift_periodic")
def detect_drift_periodic() -> dict:
    results = detect_drift_for_active_goals()
    summary = {
        "checked": len(results),
        "drifted": sum(1 for r in results if r.drifted),
        "events_emitted": sum(1 for r in results if r.event_emitted),
    }
    logger.info("goals.detect_drift_periodic: %s", summary)
    return summary


@shared_task(name="goals.open_weekly_reflections")
def open_weekly_reflections(target_iso: str | None = None) -> dict:
    if target_iso:
        from datetime import date as _date
        week_start = monday_of(_date.fromisoformat(target_iso))
    else:
        week_start = monday_of(timezone.localdate())
    created = open_reflections_for_week(week_start=week_start)
    return {"week_start": week_start.isoformat(), "stubs_created": created}
