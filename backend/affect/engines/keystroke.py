"""Keystroke-dynamics affect estimator.

Inputs are *summary statistics only* — never raw keystrokes — so the
engine never holds a biometric template. The frontend collects:

  ``inter_key_intervals_ms``: list[int]   # gap between successive keys
  ``backspace_ratio``: float             # backspaces / total keys
  ``burst_count``: int                   # contiguous bursts of <80ms
  ``pause_count``: int                   # gaps >2000ms

We map them onto valence (negative when frustrated) and arousal
(high when typing fast or with many bursts) using a simple, fully
auditable rule set. Confidence falls when the sample size is small.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Iterable, Mapping


@dataclass
class KeystrokeSnapshot:
    valence: float
    arousal: float
    confidence: float
    label: str
    features: dict = field(default_factory=dict)


def _safe_mean(values: Iterable[float]) -> float:
    values = list(values)
    return float(statistics.mean(values)) if values else 0.0


def _safe_stdev(values: Iterable[float]) -> float:
    values = list(values)
    return float(statistics.pstdev(values)) if len(values) > 1 else 0.0


def estimate(payload: Mapping, *, min_sample: int = 10) -> KeystrokeSnapshot:
    intervals = list(payload.get("inter_key_intervals_ms", []) or [])
    backspace_ratio = max(0.0, min(1.0, float(payload.get("backspace_ratio", 0.0))))
    burst_count = int(payload.get("burst_count", 0))
    pause_count = int(payload.get("pause_count", 0))

    if len(intervals) < min_sample:
        return KeystrokeSnapshot(
            valence=0.0,
            arousal=0.0,
            confidence=max(0.0, len(intervals) / max(min_sample, 1)),
            label="insufficient_sample",
            features={
                "interval_mean_ms": _safe_mean(intervals),
                "interval_std_ms": _safe_stdev(intervals),
                "backspace_ratio": backspace_ratio,
                "burst_count": burst_count,
                "pause_count": pause_count,
                "sample_size": len(intervals),
            },
        )

    interval_mean = _safe_mean(intervals)
    interval_std = _safe_stdev(intervals)
    burst_density = burst_count / max(len(intervals), 1)
    pause_density = pause_count / max(len(intervals), 1)

    arousal = max(
        0.0,
        min(
            1.0,
            0.55 * burst_density
            + 0.35 * (1.0 - min(interval_mean / 600.0, 1.0))
            + 0.10 * min(interval_std / 400.0, 1.0),
        ),
    )

    valence_raw = (
        -0.55 * backspace_ratio
        - 0.30 * pause_density
        + 0.15 * burst_density
    )
    valence = max(-1.0, min(1.0, valence_raw))

    if backspace_ratio > 0.30 and pause_density > 0.15:
        label = "frustrated"
    elif arousal > 0.65 and valence > 0.0:
        label = "engaged"
    elif pause_density > 0.25 and arousal < 0.35:
        label = "disengaged"
    elif valence < -0.4:
        label = "stressed"
    else:
        label = "neutral"

    confidence = max(0.0, min(1.0, len(intervals) / 60.0))
    return KeystrokeSnapshot(
        valence=valence,
        arousal=arousal,
        confidence=confidence,
        label=label,
        features={
            "interval_mean_ms": interval_mean,
            "interval_std_ms": interval_std,
            "backspace_ratio": backspace_ratio,
            "burst_density": burst_density,
            "pause_density": pause_density,
            "sample_size": len(intervals),
        },
    )
