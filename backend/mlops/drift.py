"""
Lightweight drift detection (Evidently-equivalent contract).

Operates on per-feature numeric/categorical samples comparing a reference
window vs a current window. Numeric features use the two-sample
Kolmogorov-Smirnov test; categorical features use chi-square. The combined
``severity`` is derived from the worst per-feature p-value to keep the
output explainable.
"""
from __future__ import annotations

import logging
from typing import Iterable

import numpy as np

from .models import DriftReport, ModelVersion

logger = logging.getLogger("palp")

_NUMERIC_KS_THRESHOLDS = {
    "minor": 0.10,
    "major": 0.01,
    "critical": 0.001,
}


def detect_numeric_drift(reference: Iterable[float], current: Iterable[float]) -> dict:
    """KS two-sample test. Returns p_value + drift_score (1 - p) for ranking."""
    ref = np.asarray(list(reference), dtype=float)
    cur = np.asarray(list(current), dtype=float)
    if ref.size < 5 or cur.size < 5:
        return {"p_value": None, "drift_score": 0.0, "skipped": "insufficient_sample"}

    try:
        from scipy import stats
    except ImportError:
        return {"p_value": None, "drift_score": 0.0, "skipped": "scipy_missing"}

    ks_stat, p = stats.ks_2samp(ref, cur)
    return {
        "p_value": float(p),
        "drift_score": float(1.0 - p),
        "ks_stat": float(ks_stat),
        "n_ref": int(ref.size),
        "n_cur": int(cur.size),
    }


def detect_categorical_drift(
    reference: Iterable[str], current: Iterable[str]
) -> dict:
    """Chi-square test of independence on category counts."""
    from collections import Counter

    ref = Counter(reference)
    cur = Counter(current)
    categories = sorted(set(ref) | set(cur))
    if not categories:
        return {"p_value": None, "drift_score": 0.0, "skipped": "no_categories"}

    try:
        from scipy import stats
    except ImportError:
        return {"p_value": None, "drift_score": 0.0, "skipped": "scipy_missing"}

    table = [[ref.get(c, 0) for c in categories], [cur.get(c, 0) for c in categories]]
    if sum(table[0]) == 0 or sum(table[1]) == 0:
        return {"p_value": None, "drift_score": 0.0, "skipped": "empty_window"}

    _, p, _, _ = stats.chi2_contingency(table)
    return {
        "p_value": float(p),
        "drift_score": float(1.0 - p),
        "n_categories": len(categories),
    }


def _classify_severity(per_feature_p: list[float | None]) -> str:
    """Combine per-feature p-values into a single severity label."""
    valid = [p for p in per_feature_p if p is not None]
    if not valid:
        return DriftReport.Severity.NONE
    worst = min(valid)
    if worst < _NUMERIC_KS_THRESHOLDS["critical"]:
        return DriftReport.Severity.CRITICAL
    if worst < _NUMERIC_KS_THRESHOLDS["major"]:
        return DriftReport.Severity.MAJOR
    if worst < _NUMERIC_KS_THRESHOLDS["minor"]:
        return DriftReport.Severity.MINOR
    return DriftReport.Severity.NONE


def build_drift_report(
    *,
    model_version: ModelVersion,
    reference_features: dict[str, dict],
    current_features: dict[str, dict],
    window_start,
    window_end,
) -> DriftReport:
    """Build and persist a ``DriftReport`` row.

    ``reference_features`` and ``current_features`` are dicts keyed by
    feature name with ``{"kind": "numeric"|"categorical", "values": [...]}``.
    Feature names must match between reference and current.
    """
    summary: dict[str, dict] = {}
    p_values: list[float | None] = []
    sample_size = 0

    for feat_name, ref_spec in reference_features.items():
        cur_spec = current_features.get(feat_name)
        if cur_spec is None:
            summary[feat_name] = {"skipped": "no_current_window"}
            continue

        kind = ref_spec.get("kind", "numeric")
        if kind == "categorical":
            res = detect_categorical_drift(ref_spec["values"], cur_spec["values"])
        else:
            res = detect_numeric_drift(ref_spec["values"], cur_spec["values"])

        summary[feat_name] = res
        p_values.append(res.get("p_value"))
        sample_size += res.get("n_cur", len(list(cur_spec.get("values", [])))) or 0

    severity = _classify_severity(p_values)
    drift_detected = severity != DriftReport.Severity.NONE

    report = DriftReport.objects.create(
        model_version=model_version,
        window_start=window_start,
        window_end=window_end,
        drift_detected=drift_detected,
        severity=severity,
        feature_summary=summary,
        sample_size=sample_size,
    )
    logger.info(
        "Drift report",
        extra={
            "model_version_id": model_version.id,
            "severity": severity,
            "n_features": len(summary),
        },
    )
    return report
