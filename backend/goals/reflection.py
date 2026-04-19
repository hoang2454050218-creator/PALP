"""
Weekly reflection cycle service.

Two callers:

* ``submit_reflection(...)`` — invoked by the API view when the student
  fills the weekly journal. Persists ``GoalReflection`` + optional
  ``EffortRating`` and ``StrategyEffectiveness`` rows in one atomic
  transaction, then emits ``reflection_submitted``.

* ``open_reflections_for_week(week_start)`` — Celery-driven helper that
  ensures every student with an active ``WeeklyGoal`` has a stub
  ``GoalReflection`` row. The frontend uses the stub to render the
  prompt; submission populates the text fields.

Both are idempotent so the Saturday 18:00 ICT cron can be retried
without duplicating reflections.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from django.db import transaction
from django.utils import timezone

from accounts.models import User

logger = logging.getLogger("palp")


@dataclass
class ReflectionSubmission:
    weekly_goal_id: int
    learned_text: str = ""
    struggle_text: str = ""
    next_priority_text: str = ""
    effort_rating: int | None = None
    effort_note: str = ""
    strategy_effectiveness: dict[int, dict] | None = None  # strategy_plan_id -> {rating, will_repeat, note}


@transaction.atomic
def submit_reflection(*, student: User, payload: ReflectionSubmission):
    from .models import (
        EffortRating,
        GoalReflection,
        StrategyEffectiveness,
        StrategyPlan,
        WeeklyGoal,
    )

    weekly = WeeklyGoal.objects.select_for_update().get(
        pk=payload.weekly_goal_id, student=student,
    )

    reflection, _ = GoalReflection.objects.update_or_create(
        weekly_goal=weekly,
        defaults={
            "student": student,
            "week_start": weekly.week_start,
            "learned_text": payload.learned_text or "",
            "struggle_text": payload.struggle_text or "",
            "next_priority_text": payload.next_priority_text or "",
            "submitted_at": timezone.now(),
        },
    )

    if payload.effort_rating is not None:
        if not (1 <= int(payload.effort_rating) <= 5):
            raise ValueError("effort_rating must be 1..5")
        EffortRating.objects.update_or_create(
            weekly_goal=weekly,
            defaults={
                "student": student,
                "rating": int(payload.effort_rating),
                "note": payload.effort_note or "",
            },
        )

    if payload.strategy_effectiveness:
        for strat_id, body in payload.strategy_effectiveness.items():
            try:
                strat = StrategyPlan.objects.get(pk=int(strat_id), weekly_goal=weekly)
            except StrategyPlan.DoesNotExist:
                logger.warning(
                    "submit_reflection: ignoring unknown strategy_plan_id=%s for weekly_goal=%s",
                    strat_id, weekly.id,
                )
                continue
            rating = int(body.get("rating", 0))
            if not (1 <= rating <= 5):
                continue
            StrategyEffectiveness.objects.update_or_create(
                strategy_plan=strat,
                defaults={
                    "student": student,
                    "rating": rating,
                    "will_repeat": bool(body.get("will_repeat", False)),
                    "note": body.get("note") or "",
                },
            )

    try:
        from events.emitter import emit_event
        from events.models import EventLog

        emit_event(
            EventLog.EventName.REFLECTION_SUBMITTED,
            actor=student,
            actor_type=EventLog.ActorType.STUDENT,
            properties={
                "reflection_id": reflection.id,
                "weekly_goal_id": weekly.id,
                "effort_rating": payload.effort_rating,
                "free_text_word_count": _word_count(reflection),
            },
            confirmed=True,
        )
    except Exception:
        logger.exception("Failed to emit reflection_submitted for reflection=%s", reflection.id)

    return reflection


def _word_count(reflection) -> int:
    return sum(
        len((t or "").split())
        for t in (reflection.learned_text, reflection.struggle_text, reflection.next_priority_text)
    )


def open_reflections_for_week(*, week_start: date) -> int:
    """Ensure a stub GoalReflection exists for each student with an active WeeklyGoal."""
    from .models import GoalReflection, WeeklyGoal

    created_count = 0
    for wg in WeeklyGoal.objects.filter(week_start=week_start).select_related("student"):
        _, created = GoalReflection.objects.get_or_create(
            weekly_goal=wg,
            defaults={
                "student": wg.student,
                "week_start": wg.week_start,
            },
        )
        if created:
            created_count += 1
    return created_count
