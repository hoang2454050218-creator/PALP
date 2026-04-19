"""
CUPED — Controlled-experiment Using Pre-Existing Data
(Deng et al. 2013).

Given a post-experiment outcome ``y`` and a pre-experiment covariate ``x``
(typically the same metric measured during the pre-period), CUPED
constructs an adjusted outcome ``y_adj = y - theta * (x - mean(x))``
with ``theta = cov(y, x) / var(x)``. The ATE on ``y_adj`` is unbiased
relative to the ATE on ``y`` but has lower variance, which means a
smaller sample size achieves the same power.

This implementation is pure NumPy and returns plain Python floats so the
caller can serialise the result into ``CausalEvaluation.estimate_json``.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np


def cuped_theta(y: Iterable[float], x: Iterable[float]) -> float:
    y_arr = np.asarray(list(y), dtype=float)
    x_arr = np.asarray(list(x), dtype=float)
    if y_arr.size != x_arr.size:
        raise ValueError("y and x must have the same length")
    if x_arr.size < 2:
        return 0.0
    var_x = float(np.var(x_arr, ddof=1))
    if var_x == 0:
        return 0.0
    cov = float(np.cov(y_arr, x_arr, ddof=1)[0, 1])
    return cov / var_x


def cuped_adjusted(
    y: Iterable[float], x: Iterable[float], theta: float | None = None
) -> np.ndarray:
    y_arr = np.asarray(list(y), dtype=float)
    x_arr = np.asarray(list(x), dtype=float)
    if theta is None:
        theta = cuped_theta(y_arr, x_arr)
    return y_arr - theta * (x_arr - x_arr.mean())


def variance_reduction(y: Iterable[float], x: Iterable[float]) -> dict:
    """Return diagnostic info about how much CUPED reduced variance.

    ``reduction_pct`` near 0 means the covariate carried no signal; near
    1 means CUPED is highly effective.
    """
    y_arr = np.asarray(list(y), dtype=float)
    x_arr = np.asarray(list(x), dtype=float)
    if y_arr.size < 2:
        return {"theta": 0.0, "var_y": 0.0, "var_y_adj": 0.0, "reduction_pct": 0.0}
    theta = cuped_theta(y_arr, x_arr)
    y_adj = cuped_adjusted(y_arr, x_arr, theta)
    var_y = float(np.var(y_arr, ddof=1))
    var_y_adj = float(np.var(y_adj, ddof=1))
    reduction = 1.0 - (var_y_adj / var_y) if var_y > 0 else 0.0
    return {
        "theta": float(theta),
        "var_y": var_y,
        "var_y_adj": var_y_adj,
        "reduction_pct": float(reduction),
    }
