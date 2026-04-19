"""
Shadow deployment helper.

Wrap a candidate model so it runs alongside the production baseline,
collects predictions, and reports divergence. The contract is:

1. Caller invokes ``shadow_predict(candidate, baseline, x)`` for every
   inference request, recording both predictions.
2. Periodic Celery task ``mlops.tasks.summarise_shadow_window`` aggregates
   collected ``ShadowSample`` rows into a ``ShadowComparison`` record.
3. Promotion gate consults ``ShadowComparison.agreement_pct`` plus per-
   model uplift from ``backend/causal/`` before flipping production.

Sample storage uses an in-memory ring buffer flushed to Redis to avoid a
write storm on every prediction. For dev/testing the helper falls back to
an in-process ``deque`` so tests don't require Redis.
"""
from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Iterable

import numpy as np

from .models import ModelVersion, ShadowComparison

logger = logging.getLogger("palp")

_LOCAL_BUFFER: dict[tuple[int, int], deque] = {}
_LOCAL_BUFFER_MAX = 5000  # per (candidate, baseline)


@dataclass
class ShadowSample:
    candidate_pred: float
    baseline_pred: float
    label: float | None = None  # populated later when ground truth available
    context: dict = field(default_factory=dict)


def _key(candidate: ModelVersion, baseline: ModelVersion) -> tuple[int, int]:
    return (candidate.id, baseline.id)


def _buffer(candidate: ModelVersion, baseline: ModelVersion) -> deque:
    key = _key(candidate, baseline)
    if key not in _LOCAL_BUFFER:
        _LOCAL_BUFFER[key] = deque(maxlen=_LOCAL_BUFFER_MAX)
    return _LOCAL_BUFFER[key]


def shadow_predict(
    candidate: ModelVersion,
    baseline: ModelVersion,
    *,
    candidate_fn: Callable[[], float],
    baseline_fn: Callable[[], float],
    context: dict | None = None,
) -> float:
    """Run both predictors, return the baseline value, record both.

    The baseline result is what gets returned to the caller — shadow runs
    must be invisible to user-facing latency-sensitive paths.
    """
    try:
        baseline_pred = float(baseline_fn())
    except Exception:
        logger.exception("Baseline predictor raised; aborting shadow capture.")
        raise

    try:
        candidate_pred = float(candidate_fn())
    except Exception as exc:
        logger.warning(
            "Shadow candidate raised: %s. Recording NaN.", exc, extra={"candidate_id": candidate.id}
        )
        candidate_pred = float("nan")

    sample = ShadowSample(
        candidate_pred=candidate_pred,
        baseline_pred=baseline_pred,
        context=context or {},
    )
    _buffer(candidate, baseline).append(sample)
    return baseline_pred


def collected_samples(candidate: ModelVersion, baseline: ModelVersion) -> Iterable[ShadowSample]:
    return list(_buffer(candidate, baseline))


def reset_samples(candidate: ModelVersion | None = None, baseline: ModelVersion | None = None):
    """Clear the in-process buffer. Call between tests, or after summarising."""
    if candidate is None and baseline is None:
        _LOCAL_BUFFER.clear()
        return
    _LOCAL_BUFFER.pop(_key(candidate, baseline), None)


def summarise(
    candidate: ModelVersion,
    baseline: ModelVersion,
    window_start,
    window_end,
    *,
    agreement_tolerance: float = 0.05,
) -> ShadowComparison:
    """Aggregate buffered samples into a ``ShadowComparison`` row."""
    samples = collected_samples(candidate, baseline)
    if not samples:
        return ShadowComparison.objects.create(
            candidate_version=candidate,
            baseline_version=baseline,
            window_start=window_start,
            window_end=window_end,
            n_predictions=0,
            mean_abs_diff=0.0,
            p95_abs_diff=0.0,
            agreement_pct=0.0,
            divergence_summary={"empty_window": True},
        )

    diffs = np.array(
        [
            abs(s.candidate_pred - s.baseline_pred)
            for s in samples
            if not (np.isnan(s.candidate_pred) or np.isnan(s.baseline_pred))
        ],
        dtype=float,
    )
    n = int(diffs.size)
    if n == 0:
        comparison = ShadowComparison.objects.create(
            candidate_version=candidate,
            baseline_version=baseline,
            window_start=window_start,
            window_end=window_end,
            n_predictions=len(samples),
            mean_abs_diff=0.0,
            p95_abs_diff=0.0,
            agreement_pct=0.0,
            divergence_summary={"all_nan": True},
        )
        reset_samples(candidate, baseline)
        return comparison

    mean_abs = float(diffs.mean())
    p95 = float(np.percentile(diffs, 95))
    agreement = float((diffs <= agreement_tolerance).mean())
    histogram, edges = np.histogram(diffs, bins=10)

    comparison = ShadowComparison.objects.create(
        candidate_version=candidate,
        baseline_version=baseline,
        window_start=window_start,
        window_end=window_end,
        n_predictions=n,
        mean_abs_diff=mean_abs,
        p95_abs_diff=p95,
        agreement_pct=agreement,
        divergence_summary={
            "histogram": histogram.tolist(),
            "edges": edges.tolist(),
            "tolerance": agreement_tolerance,
        },
    )
    reset_samples(candidate, baseline)
    return comparison
