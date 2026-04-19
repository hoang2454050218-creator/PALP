"""Beta-Bernoulli Thompson sampler — pure NumPy.

Closed-form: each arm has a Beta(alpha, beta) posterior. To select an
arm we draw one sample per arm and pick the highest. To update we add
the reward to alpha and (1 - reward) to beta.

The sampler is deterministic when given a seeded NumPy ``Generator`` —
the service layer constructs one per request from the experiment's
configured seed + the decision context so tests can assert exact
choices.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class ArmPosteriorState:
    arm_id: int
    alpha: float
    beta: float


@dataclass
class ThompsonChoice:
    arm_id: int
    sampled_value: float
    samples: dict[int, float]


def thompson_select(
    *, posteriors: list[ArmPosteriorState], rng: np.random.Generator,
) -> ThompsonChoice:
    """Draw one sample per posterior; return the arm with the largest sample."""
    if not posteriors:
        raise ValueError("posteriors must be non-empty")
    samples: dict[int, float] = {}
    best_arm = posteriors[0].arm_id
    best_value = -1.0
    for state in posteriors:
        # Beta sample with the same alpha/beta convention as the model.
        value = float(rng.beta(max(state.alpha, 1e-6), max(state.beta, 1e-6)))
        samples[state.arm_id] = value
        if value > best_value:
            best_value = value
            best_arm = state.arm_id
    return ThompsonChoice(
        arm_id=best_arm, sampled_value=best_value, samples=samples,
    )


def update_posterior(
    *, alpha: float, beta: float, reward: float,
) -> tuple[float, float]:
    """Conjugate update: new_alpha = alpha + reward, new_beta = beta + (1 - reward)."""
    reward = max(0.0, min(1.0, float(reward)))
    return alpha + reward, beta + (1.0 - reward)
