---
name: causal-experiment
description: A/B test with uplift modeling, CUPED variance reduction, doubly-robust estimator. Anti p-hacking workflow. Use when proposing/running any feature rollout that needs causal validation.
---

# Causal Experiment — Anti p-Hacking Workflow

## When to use

- Proposing new feature/model rollout (any phase)
- Editing `backend/causal/` (CausalExperiment, uplift, CUPED, runner)
- Analyzing experiment results
- Reviewing experiment design before launch
- Reporting causal claims in [PUBLICATION_ROADMAP.md](../../../docs/PUBLICATION_ROADMAP.md) papers

## Hard invariants

1. **Pre-register every experiment**: hypothesis + outcome metric + analysis method **before** data collection. Stored in `CausalExperiment` model with `pre_registered_at` timestamp.
2. **No HARKing** (Hypothesizing After Results Known): post-hoc hypotheses must be labeled "exploratory", not confirmatory.
3. **Uplift, not correlation**: report `E[Y|T=1] - E[Y|T=0]` per segment, with confidence intervals.
4. **Min sample size enforced**: per `PALP_CAUSAL["MIN_SAMPLE_SIZE"]` (default 100). Power analysis required pre-launch.
5. **CUPED for variance reduction**: use pre-experiment covariate when available (typically prior 4-week behavior).
6. **Doubly-robust default**: combine outcome model + propensity weighting → robust to either model misspec.
7. **IRB approval required** if experiment involves human subjects beyond product A/B (e.g., causal claim for paper).

## Workflow per experiment

### 1. Pre-registration

```python
# backend/causal/runner.py
from .models import CausalExperiment

experiment = CausalExperiment.objects.create(
    name="dkt_v_bkt_v2_uplift",
    hypothesis="DKT predicts mastery 15%+ better than BKT v2 in AUC",
    primary_outcome_metric="mastery_prediction_auc_30d",
    secondary_outcomes=["intervention_success_rate", "student_satisfaction_imi"],
    treatment_arms=["bkt_v2", "dkt"],
    randomization_unit="student",  # not class — avoid spillover
    sample_size_per_arm=500,
    power_analysis_inputs={"alpha": 0.05, "power": 0.80, "effect_size": 0.15},
    duration_weeks=4,
    pre_registered_at=timezone.now(),
    pre_registered_by=request.user,
    irb_approval_ref="IRB-2026-PALP-001",
)
```

Pre-registration locks: hypothesis, outcome, analysis. Changes after launch require amendment + documented rationale.

### 2. Power analysis

Compute required sample size before launch:

```python
# backend/causal/services.py
from statsmodels.stats.power import tt_ind_solve_power

def compute_required_sample(effect_size, alpha=0.05, power=0.80):
    n_per_arm = tt_ind_solve_power(
        effect_size=effect_size,
        alpha=alpha,
        power=power,
        ratio=1.0,
    )
    return int(np.ceil(n_per_arm))
```

If real cohort smaller than required → defer experiment or use Bayesian methods (less common, requires expert).

### 3. Randomization

Per `randomization_unit`:

- `student`: simple random assignment, hash(student_id, experiment_id) % len(arms)
- `class`: cluster RCT, assign whole classes (use when treatment can spill: e.g., peer feature)
- `cohort`: assign whole peer cohort
- `time-based`: switchback design (rare)

```python
# backend/causal/services.py
def assign_arm(student, experiment) -> str:
    # Stable assignment — same student always same arm in same experiment
    h = hashlib.md5(f"{student.id}_{experiment.name}".encode()).hexdigest()
    bucket = int(h[:8], 16) % len(experiment.treatment_arms)
    return experiment.treatment_arms[bucket]
```

Log assignment in `ParticipantAssignment`.

### 4. CUPED variance reduction

Use pre-experiment covariate to reduce variance:

```python
# backend/causal/cuped.py
def cuped_adjusted_outcome(y_post, x_pre):
    """CUPED: y_adj = y - theta * (x - mean_x), theta = cov(y, x) / var(x)."""
    theta = np.cov(y_post, x_pre)[0, 1] / np.var(x_pre)
    return y_post - theta * (x_pre - np.mean(x_pre))
```

Pre-period typically prior 4 weeks of same metric.

### 5. Estimation

Multiple methods, report all:

```python
# backend/causal/uplift.py
import dowhy
from causalml.inference.tree import UpliftRandomForestClassifier

def estimate_ate(experiment, df):
    """Average Treatment Effect estimation."""
    
    # Method 1: Naive difference-in-means
    naive_ate = df[df.arm == "treatment"].outcome.mean() - df[df.arm == "control"].outcome.mean()
    
    # Method 2: dowhy backdoor adjustment
    model = dowhy.CausalModel(
        data=df,
        treatment="arm",
        outcome="outcome",
        common_causes=["pre_metric", "year_of_study", "course"],
    )
    estimand = model.identify_effect()
    estimate = model.estimate_effect(estimand, method_name="backdoor.propensity_score_matching")
    
    # Method 3: Doubly-robust (causalml)
    from causalml.inference.meta import DoublyRobustLearner
    drl = DoublyRobustLearner()
    drl_ate = drl.estimate_ate(X=df[["pre_metric", "year_of_study"]], treatment=df["arm"], y=df["outcome"])
    
    return {
        "naive_ate": naive_ate,
        "dowhy_ate": estimate.value,
        "drl_ate": drl_ate,
        "ci_95": _compute_ci(estimate),
    }
```

### 6. Heterogeneity analysis (uplift modeling)

Different students respond differently to treatment:

```python
def estimate_uplift_per_segment(df):
    """Uplift = ATE in segment."""
    uplift_model = UpliftRandomForestClassifier(n_estimators=100)
    uplift_model.fit(
        X=df[features],
        treatment=df["arm"],
        y=df["outcome"],
    )
    
    return uplift_model.predict(df[features])  # uplift per row
```

Use this to identify "responders" vs "non-responders" for personalized rollout.

### 7. Robustness checks

Pre-registered:
- Sensitivity analysis (per dowhy `refute_estimate`)
- Placebo test (effect on irrelevant metric should be 0)
- Negative control outcome
- Subgroup analysis (gender, region) — also fairness check

### 8. Reporting

Pre-registered template, fill in result, no cherry-picking:

```markdown
## Experiment: {name}

- Hypothesis: {pre-registered}
- Sample size achieved: N treatment, N control
- Primary outcome: {result with CI}
  - Naive: {value}
  - DoWhy backdoor: {value}
  - Doubly-robust: {value}
- Robustness: passed / failed
- Heterogeneity: {segments responding}
- Decision: launch / iterate / kill
```

## Anti-pattern detection

| Anti-pattern | Mitigation |
|---|---|
| Stopping early when result favorable (peeking) | Pre-register stopping rule. Use sequential testing if needed. |
| Multiple testing without correction | Pre-specify family of hypotheses; Bonferroni or FDR correction |
| HARKing | Label exploratory analyses clearly |
| Selective reporting | Publish all pre-registered outcomes, including null |
| File drawer effect | Negative results published in [PUBLICATION_ROADMAP.md](../../../docs/PUBLICATION_ROADMAP.md) |
| P-value worship | Report effect size + CI, not just p-value |
| Confounding | Use propensity matching, doubly-robust, dowhy backdoor |
| Spillover | Choose appropriate randomization unit |

## Integration với MLOps

```python
# backend/causal/runner.py
def evaluate_experiment(experiment_id):
    experiment = CausalExperiment.objects.get(pk=experiment_id)
    
    # Fetch from MLflow if model-based experiment
    if experiment.model_versions:
        treatment_model = mlflow.pyfunc.load_model(experiment.model_versions["treatment"])
        control_model = mlflow.pyfunc.load_model(experiment.model_versions["control"])
    
    df = fetch_outcome_data(experiment)
    results = estimate_ate(experiment, df)
    
    # Log to MLflow
    with mlflow.start_run(experiment_id=experiment.mlflow_experiment_id):
        for method, value in results.items():
            mlflow.log_metric(method, value)
    
    # Persist
    experiment.results_json = results
    experiment.evaluated_at = timezone.now()
    experiment.save()
```

## Common pitfalls

- **Sample too small**: result is noise, not signal. Always power analysis first.
- **Spillover ignored**: peer feature with student-level random → control sees treatment via peer → bias. Use cluster RCT.
- **Selection bias**: voluntary opt-in arm → motivated students self-select → biased. Force random for confirmatory experiments.
- **CUPED on wrong covariate**: pick covariate correlated with outcome but uncorrelated with treatment.
- **Fairness blind spot**: ATE positive overall but negative for subgroup → harm. Always subgroup analysis.

## IRB-required experiments

Per [PUBLICATION_ROADMAP.md](../../../docs/PUBLICATION_ROADMAP.md):
- Anything beyond product A/B (academic causal claim)
- Anything affecting "intervention" decisions (lecturer triage)
- Anything involving emergency pipeline detection accuracy

Standing IRB protocol covers most ongoing experiments. New experiment = amendment.

## Related

- [PUBLICATION_ROADMAP.md](../../../docs/PUBLICATION_ROADMAP.md) — academic publishing
- [LEARNING_SCIENCE_FOUNDATIONS.md](../../../docs/LEARNING_SCIENCE_FOUNDATIONS.md) — theory grounding for hypotheses
- [MOTIVATION_DESIGN.md](../../../docs/MOTIVATION_DESIGN.md) — long-term retention/IMI metrics for SDT-related experiments
- [fairness-audit skill](../fairness-audit/SKILL.md) — subgroup analysis
- [dkt-engine skill](../dkt-engine/SKILL.md) — DKT vs BKT v2 experiment example
