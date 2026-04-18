"""
Service layer for A/B test assignment + statistical analysis.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Iterable

from django.db import IntegrityError, transaction

from .models import Experiment, ExperimentAssignment, ExperimentVariant

logger = logging.getLogger("palp")


def assign_variant(experiment: Experiment, user) -> ExperimentVariant | None:
    """Return a sticky variant assignment for the user.

    Sticky means the same user always gets the same variant for an
    experiment (hash-based bucketing) until the experiment ends. Returns
    ``None`` if the experiment is not running or has no variants.
    """
    if experiment.status != Experiment.Status.RUNNING:
        return None

    existing = ExperimentAssignment.objects.filter(
        experiment=experiment, user=user
    ).select_related("variant").first()
    if existing:
        return existing.variant

    variants = list(
        ExperimentVariant.objects.filter(experiment=experiment).order_by("id")
    )
    if not variants:
        return None

    chosen = _bucket_variant(experiment.name, user.id, variants)

    try:
        with transaction.atomic():
            ExperimentAssignment.objects.create(
                experiment=experiment, user=user, variant=chosen,
            )
    except IntegrityError:
        # Race condition (concurrent first hits) -- re-read.
        return ExperimentAssignment.objects.filter(
            experiment=experiment, user=user
        ).select_related("variant").first().variant
    return chosen


def _bucket_variant(
    experiment_name: str,
    user_id: int,
    variants: list[ExperimentVariant],
) -> ExperimentVariant:
    total_weight = sum(v.weight for v in variants) or 1
    h = hashlib.sha256(f"{experiment_name}:{user_id}".encode("utf-8")).hexdigest()
    bucket = int(h[:8], 16) % total_weight
    cum = 0
    for v in variants:
        cum += v.weight
        if bucket < cum:
            return v
    return variants[-1]


def assignment_map_for(user) -> dict[str, str]:
    """Map experiment_name -> variant_name for all running experiments
    the user is enrolled in. Used by middleware to inject into EventLog.
    """
    return {
        a.experiment.name: a.variant.name
        for a in ExperimentAssignment.objects
        .filter(user=user, experiment__status=Experiment.Status.RUNNING)
        .select_related("experiment", "variant")
    }


def compute_results(experiment: Experiment) -> dict:
    """Compute statistical comparison between control and treatment variants.

    For numeric metric: Welch's t-test (unequal variance, robust to outliers).
    For binary metric: chi-square test of independence.

    Returns ``{variant_name: {n, mean, std, p_value_vs_control, ...}}``.
    """
    from events.models import EventLog

    variants = list(experiment.variants.all())
    if len(variants) < 2:
        return {"error": "need_at_least_two_variants"}

    # Build per-variant sample of the primary metric. We pull from
    # EventLog.properties[primary_metric] populated by the app code or
    # KPI computation jobs.
    metric = experiment.primary_metric
    samples: dict[str, list[float]] = {v.name: [] for v in variants}

    for assignment in ExperimentAssignment.objects.filter(
        experiment=experiment
    ).select_related("variant"):
        events = EventLog.objects.filter(actor_id=assignment.user_id).values_list(
            "properties", flat=True
        )
        for props in events:
            if not isinstance(props, dict):
                continue
            value = props.get(metric)
            if value is None:
                continue
            try:
                samples[assignment.variant.name].append(float(value))
            except (TypeError, ValueError):
                continue

    control_name = variants[0].name
    control = samples[control_name]
    out: dict[str, dict] = {}
    for v in variants:
        s = samples[v.name]
        out[v.name] = {
            "n": len(s),
            "mean": (sum(s) / len(s)) if s else None,
            "is_control": v.name == control_name,
        }
        if v.name == control_name or not s or not control:
            out[v.name]["p_value_vs_control"] = None
            continue

        try:
            from scipy import stats  # local import keeps cold start cheap
        except ImportError:
            out[v.name]["p_value_vs_control"] = None
            out[v.name]["error"] = "scipy_not_installed"
            continue

        if experiment.metric_kind == Experiment.MetricKind.BINARY:
            # Chi-square: rows are variants, columns are 0/1 outcomes.
            c0 = sum(1 for x in control if x == 0)
            c1 = sum(1 for x in control if x == 1)
            v0 = sum(1 for x in s if x == 0)
            v1 = sum(1 for x in s if x == 1)
            if c0 + c1 == 0 or v0 + v1 == 0:
                out[v.name]["p_value_vs_control"] = None
                continue
            _, p, _, _ = stats.chi2_contingency([[c0, c1], [v0, v1]])
        else:
            _, p = stats.ttest_ind(control, s, equal_var=False)

        out[v.name]["p_value_vs_control"] = round(float(p), 5)
        out[v.name]["significant_at_5pct"] = bool(p < 0.05)
    return out
