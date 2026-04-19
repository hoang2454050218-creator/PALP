"""XAI service layer — DB-aware wrappers over the engines."""
from __future__ import annotations

from django.db import transaction

from explainability.engines.counterfactual import generate_for_risk
from explainability.engines.shap_lite import explain_risk_snapshot
from explainability.models import (
    CounterfactualScenario,
    ExplanationRecord,
    FeatureContribution,
)


@transaction.atomic
def explain_and_persist_risk(*, student, snapshot) -> ExplanationRecord:
    """Compute SHAP-lite + counterfactuals for a risk snapshot and store them."""
    additive = explain_risk_snapshot(snapshot)
    counterfactuals = generate_for_risk(snapshot)

    record = ExplanationRecord.objects.create(
        subject=student,
        kind=ExplanationRecord.Kind.RISK_SCORE,
        method=ExplanationRecord.Method.SHAP_LITE,
        target_object_id=str(getattr(snapshot, "id", "")),
        summary=additive.summary,
        payload={
            "score": additive.score,
            "base_value": additive.base_value,
            "contributions": [c.__dict__ for c in additive.contributions],
            "counterfactuals": [c.__dict__ for c in counterfactuals],
        },
        confidence=0.9,
        base_value=additive.base_value,
    )

    for c in additive.contributions:
        FeatureContribution.objects.create(
            explanation=record,
            feature_key=c.feature_key,
            raw_value=c.raw_value,
            contribution=c.contribution,
            rank=c.rank,
        )

    for cf in counterfactuals:
        CounterfactualScenario.objects.create(
            explanation=record,
            feature_key=cf.feature_key,
            current_value=cf.current_value,
            target_value=cf.target_value,
            expected_delta=cf.expected_delta,
            feasibility=cf.feasibility,
            actionable_hint=cf.actionable_hint,
        )

    return record
