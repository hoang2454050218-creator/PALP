---
name: risk-scoring
description: 5-dimensional RiskScoreService composite scoring (academic/behavioral/engagement/psychological/metacognitive). Use when modifying weights, components, RiskScore model, or risk endpoint logic.
---

# Risk Scoring — 5-Dimensional Composite

## When to use

- Editing `backend/risk/scoring.py` (component computation)
- Tuning `PALP_RISK_WEIGHTS` in [`backend/palp/settings/base.py`](backend/palp/settings/base.py)
- Adding new component to a dimension (e.g., new behavioral signal)
- Editing `backend/risk/views.py` endpoints `/api/risk/me/` and `/api/risk/student/<id>/`
- Integrating RiskScore into `dashboard.services.compute_early_warnings`

## Hard invariants

1. **Composite score ∈ [0, 100]**: clip and document scaling. 0 = no risk, 100 = highest.
2. **5 dimensions, weights sum to 1.0**: configurable in `PALP_RISK_WEIGHTS`. CI test verifies sum.
3. **Per-dimension subscore ∈ [0, 1]**: each component normalized before weighting.
4. **Audit log every score**: append to `RiskScore` history table on each compute (never overwrite).
5. **RBAC strict**: student sees own composite (with XAI), lecturer sees breakdown, admin sees raw history.
6. **Fairness audit per release**: scoring model goes through `backend/fairness/audit_classifier.py` (P0).
7. **Counterfactual ready**: `compute_risk_score()` returns explanation breakdown for XAI panel.

## Dimensions + components

| Dimension | Components | Source |
|---|---|---|
| `academic` | low_mastery_count, retry_failure_count, milestone_lag_pct | `MasteryState`, `TaskAttempt`, `StudentPathway` |
| `behavioral` | focus_score_avg, frustration_score_avg, give_up_count | `SignalSession` (P1B) |
| `engagement` | inactivity_days, session_quality_avg, hint_overuse_score | `EventLog`, `SignalSession`, `TaskAttempt` |
| `psychological` | wellbeing_dismissal_rate, stress_signals | `WellbeingNudge`, future affect signals |
| `metacognitive` | calibration_error_avg, overconfidence_pattern | `MetacognitiveJudgment` (P1E) |

Default weights:

```python
# backend/palp/settings/base.py
PALP_RISK_WEIGHTS = {
    "academic": 0.30,
    "behavioral": 0.25,
    "engagement": 0.20,
    "psychological": 0.10,
    "metacognitive": 0.15,
}
# Sum = 1.00, asserted in test
```

## Compute pattern

```python
# backend/risk/scoring.py
from dataclasses import dataclass
from django.conf import settings
from .models import RiskScore

@dataclass
class RiskBreakdown:
    composite: float  # 0-100
    dimensions: dict[str, float]  # dim_name -> 0-1
    components: dict[str, float]  # comp_name -> 0-1
    explanation_factors: list[dict]  # for XAI panel

def compute_risk_score(student, course=None) -> RiskBreakdown:
    """Compute 5-dim composite risk score for a student.
    
    Grounded in:
    - Macfadyen & Dawson (2010) early warning multi-signal
    - Romero & Ventura (2010) educational data mining
    """
    weights = settings.PALP_RISK_WEIGHTS
    
    components = {
        "low_mastery_count": _low_mastery_count(student, course),
        "retry_failure_count": _retry_failure_count(student, course),
        "milestone_lag_pct": _milestone_lag_pct(student, course),
        "focus_score_avg": _focus_score_avg(student),
        "frustration_score_avg": _frustration_score_avg(student),
        "give_up_count": _give_up_count(student),
        "inactivity_days": _inactivity_days(student),
        "session_quality_avg": _session_quality_avg(student),
        "hint_overuse_score": _hint_overuse_score(student),
        "wellbeing_dismissal_rate": _wellbeing_dismissal_rate(student),
        "stress_signals": _stress_signals(student),
        "calibration_error_avg": _calibration_error_avg(student),
        "overconfidence_pattern": _overconfidence_pattern(student),
    }
    
    dimensions = {
        "academic": _aggregate_dim(components, ["low_mastery_count", "retry_failure_count", "milestone_lag_pct"]),
        "behavioral": _aggregate_dim(components, ["focus_score_avg", "frustration_score_avg", "give_up_count"]),
        "engagement": _aggregate_dim(components, ["inactivity_days", "session_quality_avg", "hint_overuse_score"]),
        "psychological": _aggregate_dim(components, ["wellbeing_dismissal_rate", "stress_signals"]),
        "metacognitive": _aggregate_dim(components, ["calibration_error_avg", "overconfidence_pattern"]),
    }
    
    composite = sum(weights[dim] * dimensions[dim] for dim in dimensions) * 100
    composite = max(0, min(100, composite))  # clamp
    
    explanation = _build_explanation(components, dimensions, weights)
    
    breakdown = RiskBreakdown(
        composite=composite,
        dimensions=dimensions,
        components=components,
        explanation_factors=explanation,
    )
    
    # Persist history
    RiskScore.objects.create(
        student=student,
        course=course,
        composite=composite,
        dimensions=dimensions,
        components=components,
        computed_at=timezone.now(),
    )
    
    return breakdown
```

## Adding new component

1. Define source: which model/event provides the data
2. Implement `_<component>(student) -> float` in [`backend/risk/scoring.py`](backend/risk/scoring.py) returning 0-1 normalized
3. Add to `components` dict in `compute_risk_score`
4. Map to dimension via `_aggregate_dim`
5. Update [Model Card](../../../docs/model_cards/risk_score_v1.md) — bump version
6. Run fairness audit on holdout
7. Run causal A/B (per [causal-experiment skill](../causal-experiment/SKILL.md)) before rollout

## Adjusting weights

Weights are env-driven config:

```python
PALP_RISK_WEIGHTS = {
    "academic": float(os.environ.get("PALP_RISK_WEIGHT_ACADEMIC", 0.30)),
    "behavioral": float(os.environ.get("PALP_RISK_WEIGHT_BEHAVIORAL", 0.25)),
    "engagement": float(os.environ.get("PALP_RISK_WEIGHT_ENGAGEMENT", 0.20)),
    "psychological": float(os.environ.get("PALP_RISK_WEIGHT_PSYCH", 0.10)),
    "metacognitive": float(os.environ.get("PALP_RISK_WEIGHT_METACOG", 0.15)),
}
assert abs(sum(PALP_RISK_WEIGHTS.values()) - 1.0) < 1e-6, "Weights must sum to 1.0"
```

When changing in production:
- Run shadow deployment with new weights via [mlops shadow](../../../docs/AI_COACH_ARCHITECTURE.md#section-2)
- Causal A/B: do new weights improve outcome (intervention success)?
- Communicate change to lecturers (if they rely on threshold)
- Update Model Card version

## Endpoint pattern

```python
# backend/risk/views.py
class MyRiskScoreView(APIView):
    """Student sees own composite, no raw component values, with XAI explanation."""
    permission_classes = [IsAuthenticated, IsStudent]
    
    def get(self, request):
        breakdown = compute_risk_score(request.user)
        # Student-facing response: composite only + simplified explanation
        return Response({
            "composite": round(breakdown.composite, 1),
            "interpretation": _to_safe_label(breakdown.composite),
            "top_factors": breakdown.explanation_factors[:3],
        })

class StudentRiskScoreView(APIView):
    """Lecturer sees full breakdown with XAI panel."""
    permission_classes = [IsAuthenticated, IsLecturerOrAdmin, IsStudentInLecturerClass]
    
    def get(self, request, student_id):
        student = User.objects.get(pk=student_id)
        breakdown = compute_risk_score(student)
        return Response({
            "composite": breakdown.composite,
            "dimensions": breakdown.dimensions,
            "components": breakdown.components,
            "explanation_factors": breakdown.explanation_factors,
            "history": list(RiskScore.objects.filter(student=student).order_by("-computed_at")[:30].values()),
        })
```

## Integration with dashboard

```python
# backend/dashboard/services.py
def compute_early_warnings(class_id):
    # ... existing 4 trigger types
    
    # NEW: trigger #5 — composite RiskScore high
    students = list_students(class_id)
    for student in students:
        breakdown = compute_risk_score(student)
        if breakdown.composite > 70:
            create_alert(
                student=student,
                trigger_type="composite_risk",
                severity="red" if breakdown.composite > 85 else "yellow",
                evidence={
                    "composite": breakdown.composite,
                    "top_factors": breakdown.explanation_factors[:3],
                },
            )
```

Don't replace existing 4 triggers — add as 5th. Lecturer sees both.

## XAI integration (P6A)

Composite score MUST have explanation interface. Per [PRIVACY_V2_DPIA.md](../../../docs/PRIVACY_V2_DPIA.md) section 3.1 + GDPR Art.22.

```python
# backend/explainability/services.py
def explain_risk(student, level="student") -> dict:
    breakdown = compute_risk_score(student)
    
    if level == "student":
        return {
            "score": breakdown.composite,
            "top_3_factors": _humanize_factors(breakdown.explanation_factors[:3]),
            "counterfactual": _build_counterfactual(breakdown),
            # E.g., "Nếu bạn tăng focus_minutes 30%, risk giảm từ 72 → 45"
        }
    elif level == "lecturer":
        return {
            "shap_waterfall": _shap_explain(breakdown),
            "all_factors": breakdown.explanation_factors,
            "counterfactual_table": _all_counterfactuals(breakdown),
        }
```

## Common pitfalls

- **Weights not summing to 1.0**: composite drift, hard to compare students; CI test catches
- **Component returning unbounded value**: clamp to [0, 1] always, document max
- **Forgetting to persist `RiskScore`**: history view breaks, no audit trail
- **Hardcoding thresholds**: use settings or `dashboard.services` constants
- **Skipping fairness audit**: discriminatory model in prod
- **No explanation**: legal exposure (GDPR Art.22)
- **Recompute every request**: expensive — cache per (student, last_signal_change) for 5 min

## Test coverage

- Each component function: unit test with edge cases (no data, max data)
- `compute_risk_score`: integration test with fixture student
- Fairness audit: subgroup parity (per [fairness-audit skill](../fairness-audit/SKILL.md))
- API endpoint: RBAC matrix per [privacy-gate skill](../privacy-gate/SKILL.md)

## Related

- [PEER_ENGINE_DESIGN.md](../../../docs/PEER_ENGINE_DESIGN.md) — RiskScore feeds herd cluster detector
- [LEARNING_SCIENCE_FOUNDATIONS.md](../../../docs/LEARNING_SCIENCE_FOUNDATIONS.md) section 2.11
- [model_cards/](../../../docs/model_cards/) — RiskScore model card
- [signals-pipeline skill](../signals-pipeline/SKILL.md) — input signals
- [fairness-audit skill](../fairness-audit/SKILL.md)
- [xai-interpretation skill](../xai-interpretation/SKILL.md) — explanation generation
