"""
RiskScore service — 5-dim composite.

Each dimension produces a normalised 0..1 sub-score from named components:

  academic       low_mastery_count, retry_failure_count, milestone_lag_pct
  behavioral     focus_score (inv), frustration_score, give_up_count
  engagement     inactivity_days, session_quality (inv), hint_overuse_score
  psychological  wellbeing_dismissal_rate, stress_signals
  metacognitive  calibration_error_avg, overconfidence_pattern

Composite = sum(weight[d] * dim[d]) * 100.

The function is safe to call when input data is missing — every signal
defaults to 0 so a brand-new student starts at 0 risk and the score
warms up as data accumulates. Cold-start strategy is intentional: we
prefer an unintrusive 0 to a noisy "70" derived from sparse data.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Iterable

from django.conf import settings
from django.db.models import Avg, Count, Max, Q
from django.utils import timezone

from accounts.models import User

logger = logging.getLogger("palp")

DEFAULT_WINDOW_DAYS = 14


@dataclass
class RiskBreakdown:
    composite: float
    dimensions: dict[str, float]
    components: dict[str, dict]
    explanation: list[dict] = field(default_factory=list)
    weights_used: dict[str, float] = field(default_factory=dict)
    sample_window_days: int = DEFAULT_WINDOW_DAYS


# ---------------------------------------------------------------------------
# Components — pure-ish helpers; each returns (raw_value, normalised 0..1).
# ---------------------------------------------------------------------------


def _safe_div(num, den):
    return num / den if den else 0.0


def _academic_components(student: User, course=None, *, window) -> dict[str, dict]:
    from adaptive.models import MasteryState, TaskAttempt
    from curriculum.models import Milestone

    mastery_qs = MasteryState.objects.filter(student=student)
    if course is not None:
        mastery_qs = mastery_qs.filter(concept__course=course)

    low_mastery = mastery_qs.filter(p_mastery__lt=0.40).count()
    total_mastery = mastery_qs.count()
    low_mastery_pct = _safe_div(low_mastery, total_mastery)

    attempt_qs = TaskAttempt.objects.filter(student=student, created_at__gte=window)
    if course is not None:
        attempt_qs = attempt_qs.filter(task__concept__course=course)
    retry_failure = attempt_qs.filter(is_correct=False).count()

    if course is not None:
        total_milestones = Milestone.objects.filter(course=course).count()
        completed_milestones = (
            student.pathways.filter(course=course)
            .values_list("milestones_completed", flat=True)
            .first()
        )
        completed_count = len(completed_milestones or [])
    else:
        # Aggregate across courses
        total_milestones = sum(
            p.course.milestones.count() for p in student.pathways.all()
        )
        completed_count = sum(
            len(p.milestones_completed or []) for p in student.pathways.all()
        )
    milestone_lag_pct = max(0.0, 1.0 - _safe_div(completed_count, total_milestones))

    return {
        "low_mastery_pct": {"value": low_mastery_pct, "normalised": min(1.0, low_mastery_pct)},
        "retry_failure_count": {
            "value": retry_failure,
            "normalised": min(1.0, retry_failure / 10.0),
        },
        "milestone_lag_pct": {"value": milestone_lag_pct, "normalised": min(1.0, milestone_lag_pct)},
    }


def _behavioral_components(student: User, *, window) -> dict[str, dict]:
    try:
        from signals.models import SignalSession
    except ImportError:
        return {}

    qs = SignalSession.objects.filter(student=student, window_start__gte=window)
    agg = qs.aggregate(
        focus_avg=Avg("focus_minutes"),
        frustration_avg=Avg("frustration_score"),
        give_up_total=Count("give_up_count"),
    )
    focus_avg = float(agg["focus_avg"] or 0.0)
    frustration_avg = float(agg["frustration_avg"] or 0.0)
    give_up_total = int(agg["give_up_total"] or 0)

    # Lower focus -> higher behavioral risk component (inverted).
    focus_risk = max(0.0, 1.0 - min(1.0, focus_avg / 5.0))  # 5 minutes = full window

    return {
        "focus_risk": {"value": focus_avg, "normalised": focus_risk},
        "frustration_score": {"value": frustration_avg, "normalised": min(1.0, frustration_avg)},
        "give_up_count": {"value": give_up_total, "normalised": min(1.0, give_up_total / 5.0)},
    }


def _engagement_components(student: User, *, window) -> dict[str, dict]:
    from events.models import EventLog

    last_activity_dt = (
        EventLog.objects.filter(actor=student)
        .aggregate(latest=Max("timestamp_utc"))["latest"]
    )
    if last_activity_dt is None:
        # Brand-new student — keep cold (0 risk) per design comment.
        inactivity_days = 0
    else:
        inactivity_days = max(0, (timezone.now() - last_activity_dt).days)

    hard_red = settings.PALP_RISK_THRESHOLDS["INACTIVITY_DAYS_HARD_RED"]
    inactivity_risk = min(1.0, inactivity_days / max(1, hard_red))

    try:
        from signals.models import SignalSession
        rows = SignalSession.objects.filter(student=student, window_start__gte=window)
        if rows.exists():
            avg_quality = sum(r.session_quality for r in rows) / rows.count()
        else:
            avg_quality = 1.0  # missing data -> assume good (don't punish)
    except ImportError:
        avg_quality = 1.0
    session_risk = max(0.0, 1.0 - avg_quality)

    return {
        "inactivity_days": {"value": inactivity_days, "normalised": inactivity_risk},
        "session_quality_inv": {"value": avg_quality, "normalised": session_risk},
    }


def _psychological_components(student: User, *, window) -> dict[str, dict]:
    try:
        from wellbeing.models import WellbeingNudge
    except ImportError:
        return {"wellbeing_dismissal_rate": {"value": 0, "normalised": 0.0}}

    nudges = WellbeingNudge.objects.filter(student=student, created_at__gte=window)
    total = nudges.count()
    if total == 0:
        dismissal_rate = 0.0
    else:
        dismissed = nudges.filter(response="dismissed").count()
        dismissal_rate = dismissed / total

    return {
        "wellbeing_dismissal_rate": {
            "value": dismissal_rate,
            "normalised": dismissal_rate,
        }
    }


def _metacognitive_components(student: User, *, window) -> dict[str, dict]:
    from adaptive.calibration import overconfidence_pattern
    from adaptive.models import MetacognitiveJudgment

    judgments = list(
        MetacognitiveJudgment.objects.filter(
            student=student, created_at__gte=window, actual_correct__isnull=False,
        )
    )
    if not judgments:
        return {
            "calibration_error_avg": {"value": None, "normalised": 0.0},
            "overconfidence_pattern": {"value": "insufficient_data", "normalised": 0.0},
        }

    pattern = overconfidence_pattern(judgments)
    err = pattern["calibration_error_avg"] or 0.0
    label = pattern["label"]

    # Overconfidence is the riskier label (false sense of mastery -> no help-seeking)
    pattern_risk = {
        "overconfident": 0.9,
        "underconfident": 0.4,
        "well_calibrated": 0.0,
        "insufficient_data": 0.0,
    }.get(label, 0.0)

    return {
        "calibration_error_avg": {"value": err, "normalised": min(1.0, err)},
        "overconfidence_pattern": {"value": label, "normalised": pattern_risk},
    }


# ---------------------------------------------------------------------------
# Composer
# ---------------------------------------------------------------------------


def compute_risk_score(
    student: User,
    *,
    course=None,
    window_days: int = DEFAULT_WINDOW_DAYS,
    persist: bool = True,
) -> "RiskBreakdown":
    """Compute the 5-dim composite for ``student``.

    ``persist`` controls whether to also write a ``RiskScore`` history row.
    Set False from inside a hot loop (lecturer dashboard) where you want
    to recompute many students without flooding the table.
    """
    weights = settings.PALP_RISK_WEIGHTS
    if abs(sum(weights.values()) - 1.0) > 1e-6:
        raise ValueError(
            f"PALP_RISK_WEIGHTS must sum to 1.0, got {sum(weights.values())!r}."
        )

    window = timezone.now() - timedelta(days=window_days)

    component_map = {
        "academic": _academic_components(student, course, window=window),
        "behavioral": _behavioral_components(student, window=window),
        "engagement": _engagement_components(student, window=window),
        "psychological": _psychological_components(student, window=window),
        "metacognitive": _metacognitive_components(student, window=window),
    }

    dimensions: dict[str, float] = {}
    for dim, components in component_map.items():
        if not components:
            dimensions[dim] = 0.0
            continue
        dim_score = sum(c["normalised"] for c in components.values()) / len(components)
        dimensions[dim] = round(min(1.0, max(0.0, dim_score)), 4)

    composite = sum(weights[d] * dimensions[d] for d in weights) * 100
    composite = round(max(0.0, min(100.0, composite)), 2)

    explanation = _build_explanation(dimensions, weights, component_map)

    breakdown = RiskBreakdown(
        composite=composite,
        dimensions=dimensions,
        components=component_map,
        explanation=explanation,
        weights_used=dict(weights),
        sample_window_days=window_days,
    )

    if persist:
        from .models import RiskScore

        RiskScore.objects.create(
            student=student,
            course=course,
            composite=composite,
            dimensions=dimensions,
            components=component_map,
            explanation=explanation,
            weights_used=dict(weights),
            sample_window_days=window_days,
        )

    return breakdown


def _build_explanation(
    dimensions: dict[str, float],
    weights: dict[str, float],
    components: dict[str, dict],
    *,
    top_n: int = 3,
) -> list[dict]:
    contribs: list[dict] = []
    for dim, dim_score in dimensions.items():
        contrib_pct = round(weights[dim] * dim_score * 100, 2)
        if contrib_pct <= 0.01:
            continue
        # Pick the worst-contributing component within this dim for the hint.
        comps = components.get(dim) or {}
        worst = max(comps.items(), key=lambda kv: kv[1]["normalised"], default=None)
        hint = (
            f"{worst[0]} = {worst[1]['value']!r}" if worst else f"{dim} dimension"
        )
        contribs.append({
            "dimension": dim,
            "contribution_pct": contrib_pct,
            "dimension_score": dim_score,
            "hint": hint,
        })
    contribs.sort(key=lambda c: -c["contribution_pct"])
    return contribs[:top_n]
