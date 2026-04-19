"""SHAP-lite explainer for additive composite scores.

The risk score (Phase 1) is itself a weighted sum of dimension sub-scores:

    composite = Σ weight_i * dim_i

That structure already gives us SHAP exactly for free — each
contribution is ``(dim_i - baseline_i) * weight_i * 100``. We don't
need the full SHAP library because the predictor is linear; the
"lite" suffix is to flag the constraint.

For non-linear predictors (DKT, future neural risk score) we'll add
KernelSHAP later; for now ``shap_lite`` covers every shipped score.
"""
from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings


@dataclass
class FeatureExplanation:
    feature_key: str
    raw_value: float
    contribution: float
    rank: int


@dataclass
class AdditiveExplanation:
    score: float
    base_value: float
    contributions: list[FeatureExplanation]
    summary: str

    def total(self) -> float:
        return self.base_value + sum(c.contribution for c in self.contributions)


_BASELINE_PER_DIMENSION = 0.40  # mid-risk baseline (0..1)
_FEATURE_LABEL = {
    "academic": "Học vụ",
    "behavioral": "Hành vi",
    "engagement": "Tương tác",
    "psychological": "Tâm lý",
    "metacognitive": "Metacognitive",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def explain_risk_snapshot(snapshot) -> AdditiveExplanation:
    """Return SHAP-lite contributions for a ``risk.RiskScore`` snapshot.

    ``snapshot`` is the dataclass returned by ``risk.scoring.compute_risk_score``
    or a ``risk.models.RiskScore`` instance. Both expose ``composite`` and
    ``dimensions``.
    """
    weights = dict(getattr(settings, "PALP_RISK_WEIGHTS", {}))
    baseline = float(_BASELINE_PER_DIMENSION) * sum(weights.values()) * 100.0
    contributions: list[FeatureExplanation] = []

    for key, weight in weights.items():
        raw = float(snapshot.dimensions.get(key, _BASELINE_PER_DIMENSION))
        # Each dimension contributes (raw - baseline) * weight * 100 to
        # the composite (0..100 score). Same units as the headline.
        delta = (raw - _BASELINE_PER_DIMENSION) * float(weight) * 100.0
        contributions.append(
            FeatureExplanation(
                feature_key=key,
                raw_value=raw,
                contribution=round(delta, 4),
                rank=0,  # filled below
            )
        )

    contributions.sort(key=lambda c: -abs(c.contribution))
    for i, c in enumerate(contributions, start=1):
        c.rank = i

    composite = float(getattr(snapshot, "composite", 0.0))
    summary = _summarise(contributions, composite)
    return AdditiveExplanation(
        score=composite,
        base_value=round(baseline, 4),
        contributions=contributions,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _summarise(contributions: list[FeatureExplanation], composite: float) -> str:
    if not contributions:
        return f"Risk composite {composite:.0f}/100 — không có dữ liệu giải thích."
    top = contributions[0]
    direction = "đẩy lên" if top.contribution > 0 else "kéo xuống"
    label = _FEATURE_LABEL.get(top.feature_key, top.feature_key)
    return (
        f"Risk composite {composite:.0f}/100. "
        f"Yếu tố ảnh hưởng nhất: {label} "
        f"({direction} {abs(top.contribution):.1f} điểm)."
    )
