"""
Causal estimators in pure NumPy.

Mirrors the contract of ``causalml`` / ``dowhy`` for the cases PALP
actually uses, so the runner can compute multiple estimates of the same
ATE without dragging in heavy dependencies. When ``causalml`` becomes
mandatory we swap implementations behind the same function names.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np

from .cuped import cuped_adjusted, variance_reduction


def naive_ate(
    y: Iterable[float], treatment: Iterable[int]
) -> dict:
    """Difference in means estimate.

    Returns ATE + 95% Welch CI + per-arm sample sizes.
    """
    y_arr = np.asarray(list(y), dtype=float)
    t_arr = np.asarray(list(treatment), dtype=int)
    treat_mask = t_arr == 1
    ctrl_mask = t_arr == 0

    n_t = int(treat_mask.sum())
    n_c = int(ctrl_mask.sum())
    if n_t == 0 or n_c == 0:
        return {
            "ate": None,
            "ate_ci_low": None,
            "ate_ci_high": None,
            "p_value": None,
            "n_treatment": n_t,
            "n_control": n_c,
            "note": "empty_arm",
        }

    mean_t = float(y_arr[treat_mask].mean())
    mean_c = float(y_arr[ctrl_mask].mean())
    var_t = float(np.var(y_arr[treat_mask], ddof=1)) if n_t > 1 else 0.0
    var_c = float(np.var(y_arr[ctrl_mask], ddof=1)) if n_c > 1 else 0.0
    ate = mean_t - mean_c
    se = (var_t / n_t + var_c / n_c) ** 0.5
    ci = (ate - 1.96 * se, ate + 1.96 * se)

    p_value = None
    if se > 0:
        try:
            from scipy import stats

            _, p_value = stats.ttest_ind(
                y_arr[treat_mask], y_arr[ctrl_mask], equal_var=False
            )
            p_value = float(p_value)
        except ImportError:
            pass

    return {
        "ate": float(ate),
        "ate_ci_low": float(ci[0]),
        "ate_ci_high": float(ci[1]),
        "p_value": p_value,
        "n_treatment": n_t,
        "n_control": n_c,
        "se": float(se),
    }


def cuped_ate(
    y: Iterable[float], treatment: Iterable[int], pre_covariate: Iterable[float]
) -> dict:
    """Naive ATE on the CUPED-adjusted outcome.

    Includes ``variance_reduction_pct`` so callers can confirm the
    covariate actually helped.
    """
    y_arr = np.asarray(list(y), dtype=float)
    x_arr = np.asarray(list(pre_covariate), dtype=float)
    t_arr = np.asarray(list(treatment), dtype=int)
    if y_arr.size != x_arr.size:
        raise ValueError("y and pre_covariate must have the same length")
    y_adj = cuped_adjusted(y_arr, x_arr)
    base = naive_ate(y_adj, t_arr)
    base["variance_reduction"] = variance_reduction(y_arr, x_arr)
    base["estimator"] = "cuped_naive"
    return base


def ipw_ate(
    y: Iterable[float],
    treatment: Iterable[int],
    propensity: Iterable[float],
) -> dict:
    """Horvitz-Thompson IPW estimator.

    ``propensity[i]`` is the estimated probability that unit i was
    assigned to treatment. For RCTs this is just the assignment rate;
    for observational data the caller fits a logistic regression.
    """
    y_arr = np.asarray(list(y), dtype=float)
    t_arr = np.asarray(list(treatment), dtype=int)
    p_arr = np.asarray(list(propensity), dtype=float)
    if not np.all((p_arr > 0) & (p_arr < 1)):
        raise ValueError("propensity must be strictly between 0 and 1 (no positivity violation)")
    weight_t = t_arr / p_arr
    weight_c = (1 - t_arr) / (1 - p_arr)
    n = float(y_arr.size)
    ate = float((weight_t * y_arr).sum() / n - (weight_c * y_arr).sum() / n)
    return {
        "ate": ate,
        "n_treatment": int(t_arr.sum()),
        "n_control": int((1 - t_arr).sum()),
        "estimator": "ipw",
    }


def doubly_robust_ate(
    y: Iterable[float],
    treatment: Iterable[int],
    propensity: Iterable[float],
    mu_treatment: Iterable[float],
    mu_control: Iterable[float],
) -> dict:
    """AIPW / Doubly-robust estimator.

    Inputs:
      * ``mu_treatment[i]`` = predicted outcome under treatment for unit i
      * ``mu_control[i]`` = predicted outcome under control for unit i
      * ``propensity[i]`` = P(T=1 | X) for unit i

    The DR estimator is unbiased if **either** the propensity model
    **or** the outcome models are correctly specified. That's the property
    that earns it the "robust" name.
    """
    y_arr = np.asarray(list(y), dtype=float)
    t_arr = np.asarray(list(treatment), dtype=int)
    p_arr = np.asarray(list(propensity), dtype=float)
    mu_t = np.asarray(list(mu_treatment), dtype=float)
    mu_c = np.asarray(list(mu_control), dtype=float)
    if not np.all((p_arr > 0) & (p_arr < 1)):
        raise ValueError("propensity must be strictly between 0 and 1 (no positivity violation)")

    correction_t = (t_arr * (y_arr - mu_t)) / p_arr
    correction_c = ((1 - t_arr) * (y_arr - mu_c)) / (1 - p_arr)
    psi_treat = mu_t + correction_t
    psi_ctrl = mu_c + correction_c
    ate = float((psi_treat - psi_ctrl).mean())

    se = float(np.std(psi_treat - psi_ctrl, ddof=1) / max(1, np.sqrt(y_arr.size)))
    ci = (ate - 1.96 * se, ate + 1.96 * se)
    return {
        "ate": ate,
        "ate_ci_low": float(ci[0]),
        "ate_ci_high": float(ci[1]),
        "se": float(se),
        "n": int(y_arr.size),
        "estimator": "doubly_robust",
    }
