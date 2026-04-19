"""Differential Privacy primitives — Laplace mechanism + ε-budget tracker.

For ε-DP releases of a real-valued query with sensitivity Δf, draw
noise from Laplace(0, Δf/ε) and add it to the raw value. The
``add_laplace_noise`` helper is a pure function so unit tests can
verify the variance is correct.

The budget tracker uses ``select_for_update`` so two concurrent
requests can't double-spend ε from the same scope — important when
the dashboard refresh and a Celery beat job both call into DP queries.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
from django.db import transaction


class BudgetExceededError(Exception):
    """Raised when a query would exceed the configured ε budget."""


@dataclass
class DPResult:
    raw_value: float
    noisy_value: float
    epsilon_spent: float
    sensitivity: float
    sample_size: int


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------

def add_laplace_noise(
    *,
    raw_value: float,
    sensitivity: float,
    epsilon: float,
    rng: np.random.Generator | None = None,
) -> float:
    """Return ``raw_value + Laplace(0, sensitivity / epsilon)``."""
    if epsilon <= 0:
        raise ValueError("epsilon must be > 0")
    if sensitivity <= 0:
        raise ValueError("sensitivity must be > 0")
    rng = rng or np.random.default_rng()
    scale = sensitivity / epsilon
    noise = float(rng.laplace(loc=0.0, scale=scale))
    return float(raw_value) + noise


# ---------------------------------------------------------------------------
# Budget tracker
# ---------------------------------------------------------------------------

@transaction.atomic
def spend(
    *,
    scope: str,
    period_start: date,
    epsilon: float,
    raw_value: float,
    sensitivity: float = 1.0,
    query_kind: str = "count",
    actor=None,
    sample_size: int = 0,
    notes: str = "",
    rng: np.random.Generator | None = None,
):
    """Charge ``epsilon`` against the (scope, period) bucket and return the noisy value.

    Raises ``BudgetExceededError`` if the spend would exceed the
    configured total. Caller decides what to do (return cached, refuse,
    log + alert).
    """
    from privacy_dp.models import DPQueryLog, EpsilonBudget

    budget = (
        EpsilonBudget.objects
        .select_for_update()
        .filter(scope=scope, period_start=period_start)
        .first()
    )
    if budget is None:
        raise BudgetExceededError(
            f"No EpsilonBudget configured for scope={scope!r} period_start={period_start}"
        )

    new_spent = float(budget.epsilon_spent) + float(epsilon)
    if new_spent > float(budget.epsilon_total) + 1e-9:
        raise BudgetExceededError(
            f"Spending ε={epsilon:.4f} would exceed budget "
            f"(remaining {budget.remaining:.4f}, scope={scope!r})"
        )

    noisy = add_laplace_noise(
        raw_value=raw_value, sensitivity=sensitivity, epsilon=epsilon, rng=rng,
    )
    log = DPQueryLog.objects.create(
        budget=budget,
        actor=actor,
        mechanism=DPQueryLog.Mechanism.LAPLACE,
        query_kind=query_kind,
        epsilon_spent=epsilon,
        sensitivity=sensitivity,
        raw_value=raw_value,
        noisy_value=noisy,
        sample_size=sample_size,
        notes=notes,
    )
    budget.epsilon_spent = new_spent
    budget.save(update_fields=["epsilon_spent", "updated_at"])

    return DPResult(
        raw_value=raw_value,
        noisy_value=noisy,
        epsilon_spent=epsilon,
        sensitivity=sensitivity,
        sample_size=sample_size,
    ), log
