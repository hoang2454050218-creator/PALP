"""
Pure-function scoring helpers used by the ingest pipeline + RiskScore.

Kept here (not embedded in the ingest service) so unit tests can drive
them with synthetic events without spinning up Django models.
"""
from __future__ import annotations

from typing import Iterable


def compute_focus_minutes(focus_lost_durations_ms: Iterable[int], total_window_seconds: int = 300) -> float:
    """Estimate focus minutes inside a window from focus_lost away-durations.

    Inputs are the away-durations recorded by ``focus_lost`` events (the
    period the tab was hidden). The complement is the focused time.
    """
    away_seconds = sum(focus_lost_durations_ms) / 1000.0
    focused_seconds = max(0.0, total_window_seconds - away_seconds)
    return round(focused_seconds / 60.0, 3)


def compute_idle_minutes(idle_durations_ms: Iterable[int]) -> float:
    """Sum of idle durations (in minutes)."""
    return round(sum(idle_durations_ms) / 1000.0 / 60.0, 3)


def compute_frustration_score(frustration_intensities: Iterable[float]) -> float:
    """Aggregate per-window frustration intensity into a 0-1 score.

    We use the maximum observed intensity rather than the mean so a
    single ragequit event surfaces clearly even when other interactions
    were calm. Capped to 1.0 for downstream multiplications.
    """
    intensities = list(frustration_intensities)
    if not intensities:
        return 0.0
    return round(min(1.0, max(intensities)), 4)


def compute_session_quality(
    focus_minutes: float,
    idle_minutes: float,
    frustration_score: float,
    give_up_count: int,
) -> float:
    """0-1 quality score consumed by RiskScore engagement dimension."""
    total = focus_minutes + idle_minutes
    if total <= 0:
        return 0.0
    focus_pct = focus_minutes / total
    quality = focus_pct * (1 - frustration_score) * (1 - min(1.0, give_up_count * 0.2))
    return round(max(0.0, min(1.0, quality)), 4)
