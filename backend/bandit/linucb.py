"""LinUCB contextual bandit — pure NumPy implementation.

LinUCB (Li et al. 2010) maintains, per arm, a linear model
``E[r | x] = θᵀ x`` plus a confidence bound. The selection rule is

    a* = argmax_a  θ_aᵀ x + α · sqrt(xᵀ A_a⁻¹ x)

where ``A_a = I + Σ x xᵀ`` and ``b_a = Σ r x``. Updates after seeing
``(x, r)`` are

    A_a ← A_a + x xᵀ
    b_a ← b_a + r x

We keep a per-arm ``LinUCBArmState`` (A and b matrices serialised to
nested lists for JSON storage) and provide closed-form selection +
update functions. No torch / sklearn dependency.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np


@dataclass
class LinUCBArmState:
    arm_id: int
    A: np.ndarray  # (d, d) covariance-like matrix
    b: np.ndarray  # (d,) reward-weighted feature sum

    @classmethod
    def fresh(cls, arm_id: int, dim: int) -> "LinUCBArmState":
        return cls(arm_id=arm_id, A=np.eye(dim), b=np.zeros(dim))

    @classmethod
    def from_dict(cls, data: dict) -> "LinUCBArmState":
        return cls(
            arm_id=int(data["arm_id"]),
            A=np.asarray(data["A"], dtype=float),
            b=np.asarray(data["b"], dtype=float),
        )

    def to_dict(self) -> dict:
        return {
            "arm_id": int(self.arm_id),
            "A": self.A.tolist(),
            "b": self.b.tolist(),
        }


@dataclass
class LinUCBChoice:
    arm_id: int
    score: float
    confidence_term: float
    means: dict[int, float] = field(default_factory=dict)
    bounds: dict[int, float] = field(default_factory=dict)


def _theta(state: LinUCBArmState) -> np.ndarray:
    return np.linalg.solve(state.A, state.b)


def select(
    *,
    states: Sequence[LinUCBArmState],
    context: Sequence[float],
    alpha: float = 1.0,
) -> LinUCBChoice:
    """Closed-form LinUCB arm selection.

    ``alpha`` controls exploration; default 1.0 is a sane starting
    point for mostly-stationary recommendation problems.
    """
    if not states:
        raise ValueError("states must be non-empty")
    x = np.asarray(context, dtype=float)
    if x.ndim != 1:
        raise ValueError("context must be 1-D")

    means: dict[int, float] = {}
    bounds: dict[int, float] = {}
    best_arm = states[0].arm_id
    best_score = -np.inf
    best_conf = 0.0
    for s in states:
        if s.A.shape != (x.shape[0], x.shape[0]):
            raise ValueError(
                f"Arm {s.arm_id}: A shape {s.A.shape} != "
                f"(d, d) for d={x.shape[0]}"
            )
        theta = _theta(s)
        mean = float(theta @ x)
        ainv_x = np.linalg.solve(s.A, x)
        confidence = float(alpha * np.sqrt(max(x @ ainv_x, 0.0)))
        score = mean + confidence
        means[s.arm_id] = mean
        bounds[s.arm_id] = confidence
        if score > best_score:
            best_score = score
            best_arm = s.arm_id
            best_conf = confidence
    return LinUCBChoice(
        arm_id=best_arm,
        score=best_score,
        confidence_term=best_conf,
        means=means,
        bounds=bounds,
    )


def update(
    state: LinUCBArmState, *, context: Sequence[float], reward: float,
) -> LinUCBArmState:
    """Closed-form A/b update."""
    x = np.asarray(context, dtype=float)
    if x.ndim != 1 or x.shape[0] != state.A.shape[0]:
        raise ValueError("context dimension mismatch with arm state")
    reward = max(0.0, min(1.0, float(reward)))
    return LinUCBArmState(
        arm_id=state.arm_id,
        A=state.A + np.outer(x, x),
        b=state.b + reward * x,
    )
