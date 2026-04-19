"""
Metacognitive calibration helpers.

Phase 1E. Two paths:

1. ``record_judgment(...)`` — called when the student submits a confidence
   rating BEFORE submitting the answer. Returns the freshly created
   ``MetacognitiveJudgment`` with ``actual_correct`` still null.

2. ``finalise_judgment(...)`` — called from the existing submit flow once
   the answer has been graded. Pairs the judgment with its TaskAttempt,
   computes ``calibration_error``, emits the
   ``cognitive_calibration_recorded`` event.

The weekly Celery task ``adaptive.tasks.metacog_weekly_feedback`` (added
later) walks each student's recent judgments to detect over/under-
confidence patterns and queues a coach trigger.
"""
from __future__ import annotations

import logging
from typing import Iterable

from django.db import transaction

from events.emitter import emit_event
from events.models import EventLog

from .models import MetacognitiveJudgment, TaskAttempt

logger = logging.getLogger("palp")


@transaction.atomic
def record_judgment(
    *,
    student,
    task,
    confidence_pre: int,
    judgment_type: str = MetacognitiveJudgment.JudgmentType.JOL,
) -> MetacognitiveJudgment:
    if not (1 <= int(confidence_pre) <= 5):
        raise ValueError("confidence_pre must be 1..5")

    judgment = MetacognitiveJudgment.objects.create(
        student=student,
        task=task,
        confidence_pre=int(confidence_pre),
        judgment_type=judgment_type,
    )
    return judgment


@transaction.atomic
def finalise_judgment(
    *,
    judgment: MetacognitiveJudgment,
    task_attempt: TaskAttempt,
) -> MetacognitiveJudgment:
    """Link judgment to a graded attempt + compute calibration_error."""
    if judgment.actual_correct is not None:
        # Already finalised — idempotent
        return judgment

    judgment.task_attempt = task_attempt
    judgment.actual_correct = bool(task_attempt.is_correct)
    judgment.compute_calibration_error()
    judgment.save(update_fields=["task_attempt", "actual_correct", "calibration_error"])

    try:
        emit_event(
            EventLog.EventName.COGNITIVE_CALIBRATION_RECORDED,
            actor=judgment.student,
            actor_type=EventLog.ActorType.STUDENT,
            task=judgment.task,
            properties={
                "task_id": judgment.task_id,
                "confidence_pre": judgment.confidence_pre,
                "actual_correct": judgment.actual_correct,
                "calibration_error": judgment.calibration_error,
                "judgment_type": judgment.judgment_type,
            },
            confirmed=True,
        )
    except Exception:
        logger.exception("Failed to emit cognitive_calibration_recorded for judgment %s", judgment.id)
    return judgment


def calibration_error_avg(judgments: Iterable[MetacognitiveJudgment]) -> float | None:
    finalised = [j for j in judgments if j.calibration_error is not None]
    if not finalised:
        return None
    return round(sum(j.calibration_error for j in finalised) / len(finalised), 4)


def overconfidence_pattern(judgments: Iterable[MetacognitiveJudgment]) -> dict:
    """Diagnose over/under-confidence + the loaded miscalibration direction.

    Returns:
      {
        "n": int,
        "overconfidence_rate": float,   # high confidence + wrong
        "underconfidence_rate": float,  # low confidence + correct
        "calibration_error_avg": float | None,
        "label": "well_calibrated" | "overconfident" | "underconfident" | "insufficient_data",
      }
    """
    finalised = [j for j in judgments if j.actual_correct is not None]
    n = len(finalised)
    if n < 5:
        return {
            "n": n,
            "overconfidence_rate": 0.0,
            "underconfidence_rate": 0.0,
            "calibration_error_avg": None,
            "label": "insufficient_data",
        }

    over = sum(1 for j in finalised if j.confidence_pre >= 4 and not j.actual_correct)
    under = sum(1 for j in finalised if j.confidence_pre <= 2 and j.actual_correct)
    avg_err = calibration_error_avg(finalised)

    over_rate = over / n
    under_rate = under / n

    if over_rate > 0.30:
        label = "overconfident"
    elif under_rate > 0.30:
        label = "underconfident"
    else:
        label = "well_calibrated"

    return {
        "n": n,
        "overconfidence_rate": round(over_rate, 4),
        "underconfidence_rate": round(under_rate, 4),
        "calibration_error_avg": avg_err,
        "label": label,
    }
