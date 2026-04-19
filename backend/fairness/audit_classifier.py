"""
Pre-release classifier audit.

Calls the metric functions in ``fairness.metrics``, builds a
``FairnessAudit`` row, and returns a verdict the CI gate can rely on.
"""
from __future__ import annotations

from typing import Iterable

from django.conf import settings

from .metrics import (
    calibration_per_group,
    demographic_parity,
    equalized_odds,
    selection_rates,
)
from .models import FairnessAudit


def audit_classifier(
    *,
    target_name: str,
    y_true: Iterable[int] | None,
    y_pred: Iterable[int],
    y_score: Iterable[float] | None = None,
    sensitive_features: dict[str, Iterable],
    reviewed_by=None,
    notes: str = "",
) -> FairnessAudit:
    """Audit a classifier across one or more sensitive attributes.

    ``sensitive_features`` is a dict: ``{attribute_name: [value_per_sample]}``.
    The audit logs metrics per attribute and per intersection
    ``attr_a x attr_b`` so we catch joint-distribution discrimination that a
    single-attribute check misses.
    """
    di_threshold = float(
        getattr(settings, "PALP_FAIRNESS", {}).get("DISPARATE_IMPACT_THRESHOLD", 0.8)
    )
    eod_tolerance = float(
        getattr(settings, "PALP_FAIRNESS", {}).get("EQUALIZED_ODDS_TOLERANCE", 0.1)
    )
    cal_tolerance = float(
        getattr(settings, "PALP_FAIRNESS", {}).get("CALIBRATION_TOLERANCE", 0.05)
    )

    y_pred_list = list(y_pred)
    sample_size = len(y_pred_list)
    metrics: dict = {}
    violations: list[dict] = []

    for attr, raw_values in sensitive_features.items():
        values = list(raw_values)
        if len(values) != sample_size:
            raise ValueError(
                f"sensitive feature {attr!r} has length {len(values)} != y_pred length {sample_size}"
            )

        per_attr = {
            "selection_rates": selection_rates(y_pred_list, values),
            "demographic_parity": demographic_parity(y_pred_list, values),
        }
        if y_true is not None:
            yt = list(y_true)
            per_attr["equalized_odds"] = equalized_odds(yt, y_pred_list, values)
        if y_score is not None and y_true is not None:
            per_attr["calibration"] = calibration_per_group(yt, list(y_score), values)
        metrics[attr] = per_attr

        dp = per_attr["demographic_parity"]
        if dp.get("note") != "single_group" and dp["ratio"] < di_threshold:
            violations.append({
                "attr": attr,
                "metric": "disparate_impact_ratio",
                "observed": dp["ratio"],
                "threshold": di_threshold,
            })

        if "equalized_odds" in per_attr:
            eod = per_attr["equalized_odds"]
            if eod.get("note") != "single_group" and eod["difference"] > eod_tolerance:
                violations.append({
                    "attr": attr,
                    "metric": "equalized_odds_difference",
                    "observed": eod["difference"],
                    "threshold": eod_tolerance,
                })

        if "calibration" in per_attr:
            cal = per_attr["calibration"]
            if cal.get("note") != "single_group" and cal["max_minus_min"] > cal_tolerance:
                violations.append({
                    "attr": attr,
                    "metric": "calibration_max_minus_min",
                    "observed": cal["max_minus_min"],
                    "threshold": cal_tolerance,
                })

    # Intersectional pass — pairwise only to keep computation manageable.
    attr_names = list(sensitive_features.keys())
    for i, a1 in enumerate(attr_names):
        for a2 in attr_names[i + 1:]:
            v1 = list(sensitive_features[a1])
            v2 = list(sensitive_features[a2])
            joint = [f"{x1}__{x2}" for x1, x2 in zip(v1, v2)]
            dp = demographic_parity(y_pred_list, joint)
            metrics[f"{a1}__{a2}"] = {"demographic_parity": dp}
            if dp.get("note") != "single_group" and dp["ratio"] < di_threshold:
                violations.append({
                    "attr": f"{a1}__{a2}",
                    "metric": "disparate_impact_ratio_intersectional",
                    "observed": dp["ratio"],
                    "threshold": di_threshold,
                })

    audit = FairnessAudit.objects.create(
        target_name=target_name,
        kind=FairnessAudit.AuditKind.CLASSIFIER,
        sensitive_attributes=list(sensitive_features.keys()),
        metrics=metrics,
        violations=violations,
        passed=not violations,
        sample_size=sample_size,
        reviewed_by=reviewed_by,
        notes=notes,
    )
    return audit
