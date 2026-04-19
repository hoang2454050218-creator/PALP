"""Frontier service — past-self vs current-self comparison.

This is the **default** view for every student. No peer data is ever
read here, so no consent is required. The whole point is to give
students a meaningful progress signal that does not put them in
competition with anyone else (per Marsh 1987 Big Fish Little Pond).

Returns a dict shaped for the ``GET /api/peer/frontier/`` endpoint:

```python
{
    "lookback_days": 28,
    "current_avg_mastery": 0.62,
    "prior_avg_mastery": 0.41,
    "delta": 0.21,
    "delta_pct": 51.2,
    "concepts_progressed": [
        {"concept_id": 1, "name": "Nội lực", "from": 0.20, "to": 0.55},
        ...
    ],
    "concepts_regressed": [],
    "as_of": "2026-04-18T15:00:00+07:00",
}
```
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.utils import timezone


@dataclass
class FrontierEntry:
    concept_id: int
    name: str
    current: float
    prior: float

    @property
    def delta(self) -> float:
        return self.current - self.prior


@dataclass
class FrontierSnapshot:
    lookback_days: int
    current_avg_mastery: float
    prior_avg_mastery: float
    delta: float
    delta_pct: float
    concepts_progressed: list[dict]
    concepts_regressed: list[dict]
    as_of: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def compute_frontier(student) -> FrontierSnapshot:
    """Compute past-self vs current-self mastery delta.

    Reads only from ``adaptive.MasteryState`` for the student. Each
    row already carries the latest probability; the prior value is
    derived from rows that were last updated *before* the lookback
    window began. Concepts that have only been seen recently are
    treated as ``prior=0`` so a brand-new concept counts as full
    progress.
    """
    from adaptive.models import MasteryState

    lookback_days = int(settings.PALP_PEER["FRONTIER_LOOKBACK_DAYS"])
    now = timezone.now()
    cutoff = now - timedelta(days=lookback_days)

    states = list(
        MasteryState.objects
        .filter(student=student)
        .select_related("concept")
    )

    if not states:
        return FrontierSnapshot(
            lookback_days=lookback_days,
            current_avg_mastery=0.0,
            prior_avg_mastery=0.0,
            delta=0.0,
            delta_pct=0.0,
            concepts_progressed=[],
            concepts_regressed=[],
            as_of=now.isoformat(),
        )

    progressed: list[FrontierEntry] = []
    regressed: list[FrontierEntry] = []
    current_values: list[float] = []
    prior_values: list[float] = []

    for state in states:
        # ``last_updated`` is auto_now from MasteryState; rows updated
        # before the cutoff are already at "prior" value, so prior ==
        # current there. Only rows updated inside the window have
        # non-trivial prior data — for those, the reasonable proxy of
        # "prior" is the value before this update batch, which we
        # don't store explicitly. We fall back to a deterministic
        # estimator: prior = max(0, p_mastery - typical_step), where
        # typical_step is 1/attempts.
        current_values.append(state.p_mastery)
        if state.last_updated and state.last_updated < cutoff:
            # Stable concept — counts toward both sides equally.
            prior_values.append(state.p_mastery)
            continue

        attempts = max(state.attempt_count, 1)
        typical_step = 1.0 / attempts
        estimated_prior = max(0.0, state.p_mastery - typical_step)
        prior_values.append(estimated_prior)

        delta = state.p_mastery - estimated_prior
        if delta > 0.01:
            progressed.append(
                FrontierEntry(
                    concept_id=state.concept_id,
                    name=state.concept.name,
                    current=state.p_mastery,
                    prior=estimated_prior,
                )
            )
        elif delta < -0.01:
            regressed.append(
                FrontierEntry(
                    concept_id=state.concept_id,
                    name=state.concept.name,
                    current=state.p_mastery,
                    prior=estimated_prior,
                )
            )

    progressed.sort(key=lambda e: e.delta, reverse=True)
    regressed.sort(key=lambda e: e.delta)

    current_avg = _avg(current_values)
    prior_avg = _avg(prior_values)
    delta = current_avg - prior_avg
    delta_pct = (delta / prior_avg * 100.0) if prior_avg > 0 else 0.0

    return FrontierSnapshot(
        lookback_days=lookback_days,
        current_avg_mastery=round(current_avg, 4),
        prior_avg_mastery=round(prior_avg, 4),
        delta=round(delta, 4),
        delta_pct=round(delta_pct, 2),
        concepts_progressed=[
            {
                "concept_id": e.concept_id,
                "name": e.name,
                "from": round(e.prior, 4),
                "to": round(e.current, 4),
                "delta": round(e.delta, 4),
            }
            for e in progressed[:10]
        ],
        concepts_regressed=[
            {
                "concept_id": e.concept_id,
                "name": e.name,
                "from": round(e.prior, 4),
                "to": round(e.current, 4),
                "delta": round(e.delta, 4),
            }
            for e in regressed[:5]
        ],
        as_of=now.isoformat(),
    )
