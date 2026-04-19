"""
Goal-drift detector.

Compares each active ``WeeklyGoal.target_minutes`` against the student's
actual focus minutes accumulated in ``signals.SignalSession`` for the
same week. When the gap exceeds the configured drift threshold:

* the WeeklyGoal flips to ``status=DRIFTED``
* a ``goal_drift`` event is emitted (carrying target / actual / drift_pct)
* a placeholder ``CoachTrigger`` is logged (Phase 4 will consume this)

The detector is idempotent — re-running on the same week recomputes
``drift_pct_last_check`` without re-emitting if the value hasn't moved
significantly.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

logger = logging.getLogger("palp")

DEFAULT_DRIFT_THRESHOLD = 0.40  # 40 % gap trips a drift event


def _drift_threshold() -> float:
    return float(
        getattr(settings, "PALP_GOALS", {}).get("DRIFT_THRESHOLD_PCT", DEFAULT_DRIFT_THRESHOLD)
    )


@dataclass
class DriftCheckResult:
    weekly_goal_id: int
    target_minutes: int
    actual_minutes: float
    drift_pct: float
    drifted: bool
    event_emitted: bool


def measure_actual_focus_minutes(student, *, week_start: date) -> float:
    """Sum of focus_minutes across SignalSession in [week_start, week_start+7d)."""
    try:
        from signals.models import SignalSession
    except ImportError:
        return 0.0

    start = timezone.make_aware(datetime.combine(week_start, time.min))
    end = start + timedelta(days=7)
    agg = SignalSession.objects.filter(
        student=student,
        window_start__gte=start,
        window_start__lt=end,
    ).aggregate(total=Sum("focus_minutes"))
    return float(agg["total"] or 0.0)


def evaluate_weekly_goal(weekly_goal) -> DriftCheckResult:
    """Compute drift % and side-effect on the goal row."""
    actual = measure_actual_focus_minutes(weekly_goal.student, week_start=weekly_goal.week_start)
    target = max(0, int(weekly_goal.target_minutes))

    if target <= 0:
        drift_pct = 0.0
    else:
        drift_pct = max(0.0, (target - actual) / target)

    threshold = _drift_threshold()
    drifted = drift_pct >= threshold

    prev_drift = weekly_goal.drift_pct_last_check or 0.0
    weekly_goal.drift_pct_last_check = round(drift_pct, 4)
    weekly_goal.drift_last_checked_at = timezone.now()

    # Status transitions
    if drifted and weekly_goal.status not in {weekly_goal.Status.COMPLETED, weekly_goal.Status.ABANDONED}:
        weekly_goal.status = weekly_goal.Status.DRIFTED
    elif drift_pct < threshold and weekly_goal.status == weekly_goal.Status.DRIFTED:
        weekly_goal.status = weekly_goal.Status.IN_PROGRESS

    weekly_goal.save(update_fields=["drift_pct_last_check", "drift_last_checked_at", "status"])

    # Re-emit only when drift crosses the threshold or jumps significantly.
    cross_threshold = (drift_pct >= threshold and prev_drift < threshold)
    significant_jump = abs(drift_pct - prev_drift) >= 0.10
    event_emitted = False
    if drifted and (cross_threshold or significant_jump):
        try:
            from events.emitter import emit_event
            from events.models import EventLog

            emit_event(
                EventLog.EventName.GOAL_DRIFT,
                actor=weekly_goal.student,
                actor_type=EventLog.ActorType.STUDENT,
                properties={
                    "weekly_goal_id": weekly_goal.id,
                    "target_minutes": target,
                    "actual_minutes": round(actual, 2),
                    "drift_pct": round(drift_pct, 4),
                },
            )
            event_emitted = True
        except Exception:
            logger.exception("Failed to emit goal_drift for weekly_goal=%s", weekly_goal.id)

    return DriftCheckResult(
        weekly_goal_id=weekly_goal.id,
        target_minutes=target,
        actual_minutes=round(actual, 2),
        drift_pct=round(drift_pct, 4),
        drifted=drifted,
        event_emitted=event_emitted,
    )


def detect_drift_for_active_goals(*, today: date | None = None) -> list[DriftCheckResult]:
    """Run the detector against every active WeeklyGoal for the current week.

    Called from the Celery beat ``goals.tasks.detect_drift_periodic`` every
    6 hours.
    """
    from .models import WeeklyGoal
    from .services import monday_of

    today = today or timezone.localdate()
    week_start = monday_of(today)
    qs = WeeklyGoal.objects.filter(
        week_start=week_start,
    ).exclude(status__in=[WeeklyGoal.Status.COMPLETED, WeeklyGoal.Status.ABANDONED])
    return [evaluate_weekly_goal(wg) for wg in qs]
