"""
Fairness metrics — pure functions, no Django dependencies.

Implements the subset of fairlearn's API that PALP actually uses, without
the heavy dependency chain. Drop-in replacement when fairlearn becomes
mandatory; until then we keep cold-start cheap and deterministic.

All inputs are array-likes; outputs are plain Python floats / dicts to
keep them serialisable into ``FairnessAudit.metrics`` JSON.
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable

import numpy as np


def _to_array(x: Iterable) -> np.ndarray:
    return np.asarray(list(x))


def selection_rates(y_pred: Iterable, sensitive: Iterable) -> dict[str, float]:
    """P(y_pred=1 | group=g) for each group g.

    For multi-class predictors the caller must binarise first. Returns
    empty dict if no positive predictions overall.
    """
    y = _to_array(y_pred).astype(float)
    s = _to_array(sensitive)
    rates: dict[str, float] = {}
    for group in sorted(set(s.tolist())):
        mask = s == group
        if mask.sum() == 0:
            rates[str(group)] = 0.0
            continue
        rates[str(group)] = float(y[mask].mean())
    return rates


def demographic_parity(y_pred: Iterable, sensitive: Iterable) -> dict:
    """Demographic parity difference + ratio.

    * difference = max_g(P(y=1|g)) - min_g(P(y=1|g))
    * ratio = min_g / max_g  (the EEOC 4/5 ratio)

    Lower difference and higher ratio = fairer.
    """
    rates = selection_rates(y_pred, sensitive)
    if len(rates) < 2:
        return {"difference": 0.0, "ratio": 1.0, "rates": rates, "note": "single_group"}
    values = list(rates.values())
    hi, lo = max(values), min(values)
    diff = hi - lo
    ratio = (lo / hi) if hi > 0 else 1.0
    return {"difference": float(diff), "ratio": float(ratio), "rates": rates}


def true_positive_rates(y_true: Iterable, y_pred: Iterable, sensitive: Iterable) -> dict:
    """TPR per group. Skips groups without positives."""
    yt = _to_array(y_true).astype(int)
    yp = _to_array(y_pred).astype(int)
    s = _to_array(sensitive)
    out: dict[str, float] = {}
    for group in sorted(set(s.tolist())):
        mask = s == group
        positives = (yt[mask] == 1)
        denom = int(positives.sum())
        if denom == 0:
            continue
        out[str(group)] = float((yp[mask][positives] == 1).sum() / denom)
    return out


def false_positive_rates(y_true: Iterable, y_pred: Iterable, sensitive: Iterable) -> dict:
    yt = _to_array(y_true).astype(int)
    yp = _to_array(y_pred).astype(int)
    s = _to_array(sensitive)
    out: dict[str, float] = {}
    for group in sorted(set(s.tolist())):
        mask = s == group
        negatives = (yt[mask] == 0)
        denom = int(negatives.sum())
        if denom == 0:
            continue
        out[str(group)] = float((yp[mask][negatives] == 1).sum() / denom)
    return out


def equalized_odds(y_true: Iterable, y_pred: Iterable, sensitive: Iterable) -> dict:
    """Equalized odds difference: max(|TPR_g - TPR_g'|, |FPR_g - FPR_g'|)."""
    tpr = true_positive_rates(y_true, y_pred, sensitive)
    fpr = false_positive_rates(y_true, y_pred, sensitive)
    if len(tpr) < 2 and len(fpr) < 2:
        return {"difference": 0.0, "tpr": tpr, "fpr": fpr, "note": "single_group"}
    tpr_diff = (max(tpr.values()) - min(tpr.values())) if len(tpr) >= 2 else 0.0
    fpr_diff = (max(fpr.values()) - min(fpr.values())) if len(fpr) >= 2 else 0.0
    return {
        "difference": float(max(tpr_diff, fpr_diff)),
        "tpr_difference": float(tpr_diff),
        "fpr_difference": float(fpr_diff),
        "tpr": tpr,
        "fpr": fpr,
    }


def calibration_per_group(
    y_true: Iterable, y_score: Iterable, sensitive: Iterable
) -> dict:
    """Brier score per group for predictive-parity checks."""
    yt = _to_array(y_true).astype(float)
    ys = _to_array(y_score).astype(float)
    s = _to_array(sensitive)
    out: dict[str, float] = {}
    for group in sorted(set(s.tolist())):
        mask = s == group
        if mask.sum() == 0:
            continue
        out[str(group)] = float(np.mean((ys[mask] - yt[mask]) ** 2))
    if len(out) < 2:
        return {"per_group": out, "max_minus_min": 0.0, "note": "single_group"}
    return {
        "per_group": out,
        "max_minus_min": float(max(out.values()) - min(out.values())),
    }


def concentration_ratio(
    cluster_members: Iterable, total_population: Iterable, attribute_getter
) -> dict:
    """Per-attribute concentration check used for cluster fairness audit.

    Compares the distribution of ``attribute_getter(member)`` inside the
    cluster against the population baseline. Returns per-value ratios so
    auditors can spot ``cluster_ratio >> baseline_ratio`` patterns.
    """
    cluster = list(cluster_members)
    population = list(total_population)
    if not cluster or not population:
        return {"baseline": {}, "cluster": {}, "concentration": {}}

    base_counter = Counter(str(attribute_getter(m)) for m in population)
    cluster_counter = Counter(str(attribute_getter(m)) for m in cluster)

    base_total = sum(base_counter.values()) or 1
    cluster_total = sum(cluster_counter.values()) or 1

    baseline = {k: v / base_total for k, v in base_counter.items()}
    cluster_pct = {k: v / cluster_total for k, v in cluster_counter.items()}
    concentration = {
        k: cluster_pct[k] / max(baseline.get(k, 1e-9), 1e-9)
        for k in cluster_pct
    }
    return {"baseline": baseline, "cluster": cluster_pct, "concentration": concentration}
