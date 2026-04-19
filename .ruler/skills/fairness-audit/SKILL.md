---
name: fairness-audit
description: Pre-release fairness audit cho ML model + clustering output. CI gate fail-build nếu disparate_impact_ratio<0.8. Use before deploying any ML/clustering, before each release, when reviewing model PR.
---

# Fairness Audit — Pre-release Mandatory

## When to use

- Before deploying any ML model (RiskScore, DKT, Bandit, Survival, Affect classifier)
- Before deploying any clustering (PeerCohort, HerdCluster, k-means cohort)
- Before each release (CI gate runs `scripts/fairness_release_check.py`)
- Reviewing PR that touches `backend/fairness/`, `backend/risk/`, `backend/peer/`, `backend/dkt/`
- Investigating user complaint about discriminatory output

## Hard invariants

1. **CI gate fail-build** if `disparate_impact_ratio < 0.8` OR `equalized_odds_difference > 0.1`.
2. **Intersectional analysis**: not just gender, also gender×region, gender×economic, etc.
3. **Cluster demographic concentration**: if cluster size has >70% of one attribute when class baseline <50%, fail.
4. **Audit log** every audit run + result + reviewed-by.
5. **Owner accountability**: each model has named owner responsible for fairness; reviewer not same as owner.
6. **Document in [Model Card](../../../docs/model_cards/)**: fairness metrics required field.

## Demographic attributes tracked

Stored in `accounts.User` (encrypted, opt-in disclosure):
- `gender` (M, F, Other, Prefer_not_say)
- `region` (urban, rural, derived from address)
- `economic_band` (high, mid, low — opt-in self-report or derived from scholarship/financial aid status)
- `prior_gpa_band` (top, mid, low — pre-PALP transcript)
- `year_of_study` (1, 2, 3, 4, grad)
- `course_difficulty_band` (easy, medium, hard — derived from course historical pass rate)

Some attributes (gender, economic) require explicit consent disclosure to avoid forcing self-categorization.

## Metrics

### Demographic parity

Different subgroups should have similar selection rates:

```python
# backend/fairness/metrics.py
from fairlearn.metrics import demographic_parity_difference, demographic_parity_ratio

def check_demographic_parity(y_pred, sensitive_features):
    diff = demographic_parity_difference(y_true=None, y_pred=y_pred, sensitive_features=sensitive_features)
    ratio = demographic_parity_ratio(y_true=None, y_pred=y_pred, sensitive_features=sensitive_features)
    return {"diff": diff, "ratio": ratio}
```

Threshold: `ratio >= 0.8` (4/5 rule from EEOC).

### Equalized odds

Different subgroups should have similar TPR and FPR:

```python
from fairlearn.metrics import equalized_odds_difference

def check_equalized_odds(y_true, y_pred, sensitive_features):
    diff = equalized_odds_difference(
        y_true=y_true,
        y_pred=y_pred,
        sensitive_features=sensitive_features,
    )
    return diff
```

Threshold: `diff <= 0.1`.

### Predictive parity

Calibration should be similar across subgroups:

```python
from fairlearn.metrics import false_positive_rate, true_positive_rate
import numpy as np

def check_predictive_parity(y_true, y_pred_proba, sensitive_features, threshold=0.5):
    groups = np.unique(sensitive_features)
    calibrations = {}
    for g in groups:
        mask = sensitive_features == g
        y_true_g = y_true[mask]
        y_pred_proba_g = y_pred_proba[mask]
        # Brier score per group
        brier = np.mean((y_pred_proba_g - y_true_g) ** 2)
        calibrations[g] = brier
    return calibrations
```

Threshold: max - min < 0.05.

### Cluster demographic concentration (P3 herd detection)

```python
# backend/fairness/audit_clustering.py
def audit_clustering(cluster_members, total_class, check_attributes):
    """Check if cluster has disproportionate demographic concentration.
    
    Per PEER_ENGINE_DESIGN.md section 5.1.
    """
    results = {"passed": True, "ratios": {}, "violations": []}
    total_size = len(total_class)
    cluster_size = len(cluster_members)
    
    for attr in check_attributes:
        for value in get_attribute_values(total_class, attr):
            class_ratio = count_attr_value(total_class, attr, value) / total_size
            cluster_ratio = count_attr_value(cluster_members, attr, value) / cluster_size
            
            results["ratios"][f"{attr}={value}"] = {
                "class_baseline": class_ratio,
                "cluster_observed": cluster_ratio,
                "concentration_ratio": cluster_ratio / max(class_ratio, 0.01),
            }
            
            # Fail if cluster_ratio > 0.7 AND class_ratio < 0.5
            if cluster_ratio > 0.7 and class_ratio < 0.5:
                results["passed"] = False
                results["violations"].append({
                    "attr": attr,
                    "value": value,
                    "cluster_ratio": cluster_ratio,
                    "class_ratio": class_ratio,
                })
    
    return results
```

## Workflow per audit

### 1. Setup

```python
# backend/fairness/audit_classifier.py
def audit_model(model, X_test, y_test, sensitive_features, model_name):
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)
    
    results = {
        "model_name": model_name,
        "audit_date": timezone.now().isoformat(),
        "demographic_parity": check_demographic_parity(y_pred, sensitive_features),
        "equalized_odds": check_equalized_odds(y_test, y_pred, sensitive_features),
        "predictive_parity": check_predictive_parity(y_test, y_pred_proba, sensitive_features),
    }
    
    results["passed"] = (
        results["demographic_parity"]["ratio"] >= 0.8
        and results["equalized_odds"] <= 0.1
    )
    
    return results
```

### 2. Intersectional analysis

```python
def intersectional_audit(model, X_test, y_test, attribute_pairs):
    """Audit each pair of attributes."""
    results = {}
    for attr1, attr2 in attribute_pairs:
        intersect = X_test[attr1].astype(str) + "_" + X_test[attr2].astype(str)
        results[f"{attr1}x{attr2}"] = audit_model(model, X_test, y_test, intersect, f"{model_name}_{attr1}x{attr2}")
    return results
```

Standard pairs: gender×region, gender×economic, gender×year_of_study.

### 3. CI gate

```python
# scripts/fairness_release_check.py
"""
Run in CI before release. Exit non-zero if any model fails.
"""
import sys
from backend.fairness.audit_classifier import audit_model
from backend.mlops.registry import get_production_models

def main():
    models = get_production_models()
    failures = []
    
    for model_info in models:
        model = load_model(model_info["uri"])
        X_test, y_test, sensitive_features = load_test_data(model_info["test_dataset"])
        
        result = audit_model(model, X_test, y_test, sensitive_features, model_info["name"])
        if not result["passed"]:
            failures.append({"model": model_info["name"], "result": result})
    
    if failures:
        print("FAIRNESS GATE FAILED:")
        for f in failures:
            print(f"  {f['model']}: {f['result']}")
        sys.exit(1)
    
    print("All models passed fairness gate.")
    sys.exit(0)

if __name__ == "__main__":
    main()
```

Wire into [`.github/workflows/release.yml`](.github/workflows/release.yml):

```yaml
- name: Fairness gate
  run: python scripts/fairness_release_check.py
```

### 4. Document in Model Card

Update [`docs/model_cards/{model}.md`](../../../docs/model_cards/) — Quantitative Analyses section with audit results.

### 5. If audit fails

Don't ship. Options:
- **Reweighting**: train with sample weights to balance subgroups
- **Adversarial debiasing**: train with adversarial loss penalizing protected attribute prediction
- **Post-processing**: threshold tuning per subgroup (controversial — discuss with ethicist)
- **Feature removal**: remove features that proxy protected attribute (often degrades utility)
- **Data collection**: more data from underrepresented subgroup

Document in incident-style postmortem (per [INCIDENT_CULTURE.md](../../../docs/INCIDENT_CULTURE.md)) — system gap, not blame.

## Integration với herd detection (P3)

```python
# backend/peer/services/cluster_detector.py
from backend.fairness import audit_clustering

def detect_herd_clusters(student_class):
    # ... DBSCAN clustering ...
    
    for cluster in clusters:
        # MANDATORY audit
        audit_result = audit_clustering(
            cluster_members=cluster.members,
            total_class=student_class.members.all(),
            check_attributes=["gender", "economic_band", "region"],
        )
        cluster.fairness_audit_result = audit_result
        
        if not audit_result["passed"]:
            cluster.flagged_for_review = True
            logger.warning("HerdCluster fairness audit failed", extra={
                "cluster_id": cluster.id,
                "audit": audit_result,
            })
            # DON'T suggest action yet — flag for human review
        
        cluster.save()
```

## Common pitfalls

- **Ignoring intersectionality**: model passes per-attribute but fails per-pair (gender M is fine, region urban is fine, but gender M × region urban — discrimination)
- **Test data unrepresentative**: audit on biased test set is meaningless; ensure test stratified
- **Threshold gaming**: tweaking 0.79 to 0.81 to pass; instead address root cause
- **Skipping for "small" models**: classifier with low confidence still affects users
- **Audit only at release**: model can drift after deploy; weekly re-audit via Celery
- **No baseline**: `disparate_impact_ratio < 0.8` only meaningful if baseline rate non-trivial; small numbers → check with confidence interval

## Quarterly review

Per [INCIDENT_CULTURE.md](../../../docs/INCIDENT_CULTURE.md) section 9.1:
- Review all fairness audit failures past quarter
- Trends — improving or degrading?
- Action items — model retraining, data collection, threshold review

## Related

- [PRIVACY_V2_DPIA.md](../../../docs/PRIVACY_V2_DPIA.md) — sensitive attribute disclosure consent
- [PEER_ENGINE_DESIGN.md](../../../docs/PEER_ENGINE_DESIGN.md) section 5 — cluster fairness
- [model_cards/](../../../docs/model_cards/) — required fairness section
- [risk-scoring skill](../risk-scoring/SKILL.md) — RiskScore fairness
- [dkt-engine skill](../dkt-engine/SKILL.md) — DKT fairness
- [fairlearn library](https://fairlearn.org/)
