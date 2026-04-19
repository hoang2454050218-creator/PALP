"""FSRS-4.5 scheduler — pure Python.

Faithful port of the FSRS-4.5 update equations (Free Spaced Repetition
Scheduler). The official paper + reference implementation use 17
default weights; we ship those defaults, with the trainer flagged as a
Phase 6B follow-up.

Key concepts:

* **Stability (S)**: how many days the memory will hold to the desired
  retention threshold (default 0.9).
* **Difficulty (D)**: per-item, per-student difficulty 1..10.
* **Retrievability (R)**: probability of recall at time t, given the
  item's last review and current stability:

      R(t) = (1 + t / (9 * S)) ** -1

* **Interval**: time until R drops to the target retention.

We keep everything deterministic and pure — easy to test, easy to
shadow against future neural variants.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from django.conf import settings


# Default FSRS-4.5 weights. These come from the FSRS reference
# implementation (https://github.com/open-spaced-repetition/fsrs4anki).
DEFAULT_WEIGHTS: tuple[float, ...] = (
    0.4072, 1.1829, 3.1262, 15.4722, 7.2102, 0.5316, 1.0651,
    0.0234, 1.616, 0.1544, 1.0824, 1.9813, 0.0953, 0.2975,
    2.2042, 0.2407, 2.9466,
)
DEFAULT_RETENTION = 0.9


@dataclass
class FSRSState:
    stability: float
    difficulty: float


@dataclass
class FSRSReviewResult:
    stability: float
    difficulty: float
    interval_days: float
    retrievability_at_review: float


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def initial_state(rating: int, *, weights: tuple[float, ...] | None = None) -> FSRSState:
    """Compute initial stability + difficulty for a brand-new item."""
    w = weights or DEFAULT_WEIGHTS
    stability = max(_init_stability(rating, w), 0.1)
    difficulty = _clamp_difficulty(_init_difficulty(rating, w))
    return FSRSState(stability=stability, difficulty=difficulty)


def update(
    *,
    state: FSRSState,
    rating: int,
    elapsed_days: float,
    weights: tuple[float, ...] | None = None,
    target_retention: float | None = None,
) -> FSRSReviewResult:
    """Apply one review and return the new memory state + next interval."""
    w = weights or DEFAULT_WEIGHTS
    target_retention = target_retention or DEFAULT_RETENTION

    retrievability = retrievability_after(state.stability, elapsed_days)
    new_difficulty = _next_difficulty(state.difficulty, rating, w)

    if rating == 1:
        # AGAIN — lapse path.
        new_stability = _next_forget_stability(
            state.difficulty, state.stability, retrievability, w,
        )
    else:
        new_stability = _next_recall_stability(
            state.difficulty, state.stability, retrievability, rating, w,
        )

    new_stability = max(new_stability, 0.1)
    interval = next_interval_days(new_stability, target_retention)

    return FSRSReviewResult(
        stability=new_stability,
        difficulty=new_difficulty,
        interval_days=interval,
        retrievability_at_review=retrievability,
    )


def retrievability_after(stability: float, elapsed_days: float) -> float:
    """R(t) = (1 + t / (9*S))^(-1) — the FSRS forgetting curve."""
    if stability <= 0:
        return 0.0
    return float((1.0 + max(0.0, elapsed_days) / (9.0 * stability)) ** -1)


def next_interval_days(stability: float, retention: float = DEFAULT_RETENTION) -> float:
    """Days until R drops to ``retention``."""
    if stability <= 0 or retention <= 0 or retention >= 1:
        return 1.0
    return float(9.0 * stability * (retention ** -1 - 1.0))


# ---------------------------------------------------------------------------
# Internal — FSRS update equations
# ---------------------------------------------------------------------------

def _init_stability(rating: int, w: tuple[float, ...]) -> float:
    # w0..w3 are initial stability per rating bucket.
    return float(w[max(0, rating - 1)])


def _init_difficulty(rating: int, w: tuple[float, ...]) -> float:
    # FSRS-4.5 init difficulty: w4 - w5 * (rating - 3)
    return float(w[4]) - float(w[5]) * (rating - 3)


def _next_difficulty(current: float, rating: int, w: tuple[float, ...]) -> float:
    delta = -float(w[6]) * (rating - 3)
    raw = current + delta
    # Mean-reversion: new = w7 * init_easy + (1 - w7) * raw
    init_easy = float(w[4]) - float(w[5]) * (4 - 3)
    new = float(w[7]) * init_easy + (1.0 - float(w[7])) * raw
    return _clamp_difficulty(new)


def _next_recall_stability(
    difficulty: float,
    stability: float,
    retrievability: float,
    rating: int,
    w: tuple[float, ...],
) -> float:
    hard_penalty = float(w[15]) if rating == 2 else 1.0
    easy_bonus = float(w[16]) if rating == 4 else 1.0
    factor = (
        math.exp(float(w[8]))
        * (11.0 - difficulty)
        * (stability ** -float(w[9]))
        * (math.exp(float(w[10]) * (1.0 - retrievability)) - 1.0)
        * hard_penalty
        * easy_bonus
    )
    return stability * (1.0 + factor)


def _next_forget_stability(
    difficulty: float,
    stability: float,
    retrievability: float,
    w: tuple[float, ...],
) -> float:
    return (
        float(w[11])
        * (difficulty ** -float(w[12]))
        * ((stability + 1.0) ** float(w[13]) - 1.0)
        * math.exp(float(w[14]) * (1.0 - retrievability))
    )


def _clamp_difficulty(value: float) -> float:
    return max(1.0, min(10.0, float(value)))


# ---------------------------------------------------------------------------
# Settings hook
# ---------------------------------------------------------------------------

def get_weights() -> tuple[float, ...]:
    raw = getattr(settings, "PALP_SPACEDREP", {}).get("WEIGHTS")
    if raw and len(raw) == 17:
        return tuple(float(x) for x in raw)
    return DEFAULT_WEIGHTS


def get_target_retention() -> float:
    return float(
        getattr(settings, "PALP_SPACEDREP", {}).get("TARGET_RETENTION", DEFAULT_RETENTION)
    )
