"""
Power analysis helpers.

Provides closed-form formulas (no scipy dependency in the cold path) for
the two cases PALP uses most:

* Two-sample mean comparison (continuous outcome) — Welch t-test.
* Two-proportion comparison (binary outcome).

The functions return the **per-arm** sample size required to detect the
provided effect size at the supplied alpha + power levels. Both are
quick approximations; final pre-registration uses ``statsmodels`` when
available but the tests don't depend on it.
"""
from __future__ import annotations

import math


_Z_TABLE = {
    0.50: 0.0,
    0.80: 0.8416,
    0.90: 1.2816,
    0.95: 1.6449,
    0.975: 1.9600,  # alpha/2 = 0.025 (two-sided 0.05)
    0.99: 2.3263,
    0.995: 2.5758,
}


def _z(p: float) -> float:
    """Inverse standard-normal at p. Linear interpolation across the
    small table above. Inputs outside the table fall back to scipy.
    """
    if p in _Z_TABLE:
        return _Z_TABLE[p]
    keys = sorted(_Z_TABLE)
    for i in range(len(keys) - 1):
        if keys[i] <= p <= keys[i + 1]:
            lo, hi = keys[i], keys[i + 1]
            frac = (p - lo) / (hi - lo)
            return _Z_TABLE[lo] + frac * (_Z_TABLE[hi] - _Z_TABLE[lo])
    try:
        from scipy import stats

        return float(stats.norm.ppf(p))
    except ImportError:
        return _Z_TABLE[max(keys)]


def sample_size_per_arm_continuous(
    effect_size: float,
    *,
    alpha: float = 0.05,
    power: float = 0.80,
    two_sided: bool = True,
) -> int:
    """Per-arm n for two-sample t-test on a standardised effect size.

    Uses ``n = 2 * ((z_alpha + z_beta) / d) ** 2`` (cohen's d).
    Returns ceiling so the caller never under-allocates.
    """
    if effect_size <= 0:
        raise ValueError("effect_size must be > 0")
    z_alpha = _z(1 - alpha / 2) if two_sided else _z(1 - alpha)
    z_beta = _z(power)
    n = 2.0 * ((z_alpha + z_beta) / effect_size) ** 2
    return int(math.ceil(n))


def sample_size_per_arm_binary(
    p_control: float,
    p_treatment: float,
    *,
    alpha: float = 0.05,
    power: float = 0.80,
    two_sided: bool = True,
) -> int:
    """Per-arm n for two-proportion z-test.

    n = ((z_alpha * sqrt(2 * p_bar * (1 - p_bar)) + z_beta * sqrt(p1*(1-p1) + p2*(1-p2))) / |p1 - p2|) ** 2
    """
    if not (0 <= p_control <= 1 and 0 <= p_treatment <= 1):
        raise ValueError("Proportions must be in [0, 1].")
    diff = abs(p_treatment - p_control)
    if diff == 0:
        raise ValueError("p_treatment and p_control must differ.")
    z_alpha = _z(1 - alpha / 2) if two_sided else _z(1 - alpha)
    z_beta = _z(power)
    p_bar = (p_control + p_treatment) / 2
    num = z_alpha * math.sqrt(2 * p_bar * (1 - p_bar)) + z_beta * math.sqrt(
        p_control * (1 - p_control) + p_treatment * (1 - p_treatment)
    )
    n = (num / diff) ** 2
    return int(math.ceil(n))
