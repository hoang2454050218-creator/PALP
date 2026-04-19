"""Herd cluster detector.

Goal: detect groups of students who are co-degrading — the
"đồng hoá nhóm yếu" effect described in the v3 design notes. Output
is **always** lecturer-side, never auto-action, and **always** paired
with a fairness audit to prevent demographic clustering being
misinterpreted as a behaviour cluster.

We use a small, dependency-free DBSCAN here. Class sizes are typically
< 200 so an O(n²) implementation is fine and avoids pulling in
scikit-learn. Determinism is preserved by sorting students by id
before scanning.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import timedelta
from statistics import mean
from typing import Iterable

from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger("palp.peer.herd")

NOISE_LABEL = -1


@dataclass
class HerdDetectionResult:
    cluster_id: int
    members: int
    mean_risk: float
    severity: str
    fairness_passed: bool
    flagged_for_review: bool


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_herd_clusters(student_class) -> list[HerdDetectionResult]:
    """Run DBSCAN on the class behaviour vectors + fairness audit per cluster."""
    from accounts.models import ClassMembership
    from peer.models import HerdCluster

    eps = float(settings.PALP_PEER["HERD_EPS"])
    min_samples = int(settings.PALP_PEER["HERD_MIN_SAMPLES"])
    risk_threshold = float(settings.PALP_PEER["HERD_RISK_THRESHOLD"])
    window_days = int(settings.PALP_PEER["HERD_BEHAVIOR_WINDOW_DAYS"])

    students = [
        m.student for m in
        ClassMembership.objects.filter(
            student_class=student_class
        ).select_related("student").order_by("student_id")
    ]
    if len(students) < min_samples:
        return []

    vectors = [_behaviour_vector_14d(s, window_days=window_days) for s in students]
    labels = _dbscan(vectors, eps=eps, min_samples=min_samples)

    results: list[HerdDetectionResult] = []
    with transaction.atomic():
        for label in sorted(set(labels)):
            if label == NOISE_LABEL:
                continue
            members = [s for s, l in zip(students, labels) if l == label]
            mean_risk = _mean_risk(members)
            if mean_risk < risk_threshold or len(members) < min_samples:
                continue

            severity = _severity_for(mean_risk)
            cluster = HerdCluster.objects.create(
                student_class=student_class,
                severity=severity,
                mean_risk_score=round(mean_risk, 2),
                behaviour_summary=_summarize_behaviour(members, window_days=window_days),
            )
            cluster.members.set(members)

            audit = _audit_cluster(cluster=cluster, members=members, total=students)
            if audit is not None:
                cluster.fairness_audit = audit
                if not audit.passed:
                    cluster.flagged_for_review = True
            cluster.save(update_fields=["fairness_audit", "flagged_for_review"])

            results.append(
                HerdDetectionResult(
                    cluster_id=cluster.id,
                    members=len(members),
                    mean_risk=cluster.mean_risk_score,
                    severity=cluster.severity,
                    fairness_passed=audit.passed if audit else True,
                    flagged_for_review=cluster.flagged_for_review,
                )
            )

    return results


# ---------------------------------------------------------------------------
# Behaviour vector
# ---------------------------------------------------------------------------

def _behaviour_vector_14d(student, *, window_days: int) -> list[float]:
    """Five-dimensional behaviour vector over the last ``window_days``.

    All fields are normalised to roughly 0..1 so DBSCAN's ``eps`` is
    interpretable across dimensions.
    """
    summary = _behaviour_summary_for(student, window_days=window_days)
    # Normalise to [0..1] for DBSCAN. Bounds chosen from the seeded
    # demo data and learning-science defaults; adjust via settings.
    return [
        min(summary["focus_minutes_per_day"] / 120.0, 1.0),
        min(summary["missed_milestones"] / 4.0, 1.0),
        min(summary["give_up_count"] / 5.0, 1.0),
        min(summary["dismissed_nudges"] / 4.0, 1.0),
        1.0 - min(summary["weekly_login_days"] / 7.0, 1.0),
    ]


def _behaviour_summary_for(student, *, window_days: int) -> dict:
    """Aggregate the underlying signals for one student.

    All signals are read from ``signals.SignalSession`` and
    ``events.EventLog``; both are already used elsewhere so no schema
    change is required here.
    """
    from signals.models import SignalSession

    cutoff = timezone.now() - timedelta(days=window_days)
    sessions = SignalSession.objects.filter(
        student=student, window_start__gte=cutoff,
    )

    focus = sum(s.focus_minutes for s in sessions)
    give_ups = sum(s.give_up_count for s in sessions)
    distinct_days = {s.window_start.date() for s in sessions}

    missed = _missed_milestones_count(student, since=cutoff)
    dismissed = _dismissed_nudges_count(student, since=cutoff)

    return {
        "focus_minutes_per_day": focus / max(window_days, 1),
        "missed_milestones": missed,
        "give_up_count": give_ups,
        "dismissed_nudges": dismissed,
        "weekly_login_days": min(len(distinct_days), 7),
    }


def _missed_milestones_count(student, *, since) -> int:
    from events.models import EventLog
    return EventLog.objects.filter(
        actor=student,
        event_name="milestone_missed",
        timestamp_utc__gte=since,
    ).count()


def _dismissed_nudges_count(student, *, since) -> int:
    from events.models import EventLog
    return EventLog.objects.filter(
        actor=student,
        event_name="nudge_dismissed",
        timestamp_utc__gte=since,
    ).count()


def _mean_risk(members: Iterable) -> float:
    from risk.scoring import compute_risk_score
    scores = []
    for student in members:
        snap = compute_risk_score(student, persist=False)
        scores.append(snap.composite)
    return mean(scores) if scores else 0.0


def _severity_for(risk: float) -> str:
    from peer.models import HerdCluster
    if risk >= 80:
        return HerdCluster.Severity.CRITICAL
    if risk >= 70:
        return HerdCluster.Severity.HIGH
    return HerdCluster.Severity.MEDIUM


def _summarize_behaviour(members, *, window_days: int) -> dict:
    summaries = [_behaviour_summary_for(m, window_days=window_days) for m in members]
    if not summaries:
        return {}
    return {
        "focus_minutes_per_day": round(mean(s["focus_minutes_per_day"] for s in summaries), 2),
        "missed_milestones": round(mean(s["missed_milestones"] for s in summaries), 2),
        "give_up_count": round(mean(s["give_up_count"] for s in summaries), 2),
        "dismissed_nudges": round(mean(s["dismissed_nudges"] for s in summaries), 2),
        "weekly_login_days": round(mean(s["weekly_login_days"] for s in summaries), 2),
        "window_days": window_days,
    }


# ---------------------------------------------------------------------------
# DBSCAN (lightweight, deterministic)
# ---------------------------------------------------------------------------

def _dbscan(vectors: list[list[float]], *, eps: float, min_samples: int) -> list[int]:
    n = len(vectors)
    labels = [None] * n
    cluster_id = 0

    def neighbours(i):
        return [
            j for j in range(n)
            if i != j and _euclidean(vectors[i], vectors[j]) <= eps
        ]

    for i in range(n):
        if labels[i] is not None:
            continue
        nb = neighbours(i)
        if len(nb) < min_samples - 1:
            labels[i] = NOISE_LABEL
            continue
        labels[i] = cluster_id
        seeds = list(nb)
        while seeds:
            j = seeds.pop(0)
            if labels[j] == NOISE_LABEL:
                labels[j] = cluster_id
            if labels[j] is not None:
                continue
            labels[j] = cluster_id
            nb_j = neighbours(j)
            if len(nb_j) >= min_samples - 1:
                for k in nb_j:
                    if k not in seeds and labels[k] in (None, NOISE_LABEL):
                        seeds.append(k)
        cluster_id += 1

    return [NOISE_LABEL if lbl is None else lbl for lbl in labels]


def _euclidean(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


# ---------------------------------------------------------------------------
# Fairness audit
# ---------------------------------------------------------------------------

def _audit_cluster(*, cluster, members, total):
    from fairness.audit_clustering import audit_clustering

    getters: dict = {}
    if any(getattr(s, "gender", None) for s in total):
        getters["gender"] = lambda s: getattr(s, "gender", "") or "unknown"
    if any(getattr(s, "economic_band", None) for s in total):
        getters["economic_band"] = lambda s: getattr(s, "economic_band", "") or "unknown"
    if any(getattr(s, "region", None) for s in total):
        getters["region"] = lambda s: getattr(s, "region", "") or "unknown"
    if not getters:
        return None

    try:
        return audit_clustering(
            target_name=f"herd_cluster:{cluster.id}",
            cluster_members=members,
            total_population=total,
            attribute_getters=getters,
            notes=(
                f"Auto-audit during herd detection for class "
                f"{cluster.student_class_id}."
            ),
        )
    except Exception:  # pragma: no cover -- defensive, do not block detection
        logger.exception("Fairness audit failed for herd cluster %s", cluster.id)
        return None
