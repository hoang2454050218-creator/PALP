---
name: xai-interpretation
description: Explainable AI — SHAP, SAKT attention visualization, counterfactual explanations. Tier per audience (student simplified, lecturer technical). Compliance GDPR Art.22, NĐ 13/2023. Use when modifying backend/explainability/ or adding explanation for new model.
---

# XAI Interpretation — SHAP + Attention + Counterfactual

## When to use

- Editing `backend/explainability/` (shap_explainer, attention_viz, counterfactual, lime_explainer)
- Adding explanation for new ML model (RiskScore, DKT, Survival, Bandit, Affect)
- Modifying explanation UI components
- Reviewing PR touching `/api/explain/*` endpoints
- Compliance audit (GDPR Art.22 challenge, NĐ 13/2023 review)

## Hard invariants

1. **Every automated decision has explanation** — no black-box decisions affecting students.
2. **Tier per audience** — student simplified (3 factors + counterfactual), lecturer technical (SHAP waterfall, all factors).
3. **Cached explanations** — pre-compute top-N nightly to avoid latency on dashboard load.
4. **Explanations match model predictions** — sanity check sum of SHAP ≈ prediction - baseline.
5. **Counterfactual actionable** — suggestion must be something student can DO, not "born with X".
6. **No PII in explanation strings** — ID-based, render names client-side.
7. **Audit log** every explanation request.
8. **Compliance ready** — endpoint can serve as Art.22 right-to-explanation response.

## Per-model explanation strategy

| Model | Method | Output for student | Output for lecturer |
|---|---|---|---|
| RiskScore (P1F) | SHAP per component | Top 3 factors + counterfactual | Full waterfall + history |
| DKT/SAKT (P5A) | Attention visualization | "Concept Y influenced this prediction" | Attention heatmap + token importance |
| Survival (P5D) | SHAP + hazard curve | "Tipping point: 14 days" | Cox coefficient table + survival curve |
| Bandit (P5C) | Bandit context attribution | "Why suggested this nudge" | Arm probability distribution + reward history |
| Affect Fusion (P6D) | LIME (multimodal) | "Tone seems frustrated" | Modality contribution breakdown |
| HerdCluster (P3) | DBSCAN density-based | (lecturer-only) | Cluster centroid + member proximity |
| Jailbreak Classifier (P4C) | Token attribution | (system) | Highlighted suspicious tokens |

## Workflow when adding explanation

### 1. Choose method

| Model type | Recommended method |
|---|---|
| Linear (RiskScore weighted sum) | Direct contribution per feature |
| Tree (XGBoost, RF — if used) | TreeSHAP (fast, exact) |
| Deep model (DKT, DeepHit, classifier) | SHAP DeepExplainer or LIME, attention viz if applicable |
| Multimodal | LIME tabular fusion |
| Generative (LLM responses) | (Out of scope for XAI — use Coach safety transparency) |

### 2. Implement explainer

```python
# backend/explainability/shap_explainer.py
import shap

class SHAPExplainer:
    def __init__(self, model, background_data):
        self.model = model
        if hasattr(model, "predict_proba"):
            self.explainer = shap.TreeExplainer(model) if is_tree_model(model) else shap.DeepExplainer(model, background_data)
        else:
            self.explainer = shap.KernelExplainer(model.predict, background_data)
    
    def explain(self, X) -> dict:
        shap_values = self.explainer.shap_values(X)
        return {
            "base_value": float(self.explainer.expected_value),
            "shap_values": shap_values.tolist(),
            "feature_names": self.feature_names,
        }
```

### 3. Counterfactual generation

```python
# backend/explainability/counterfactual.py
def generate_counterfactual(model, instance, target_change, feature_constraints):
    """Find minimal change to features that achieves target prediction change.
    
    Use DiCE (Diverse Counterfactual Explanations) library or custom optimization.
    """
    import dice_ml
    
    explainer = dice_ml.Dice(
        data_interface=...,
        model_interface=...,
    )
    
    cf = explainer.generate_counterfactuals(
        instance,
        total_CFs=3,
        desired_class=target_change,
        features_to_vary=actionable_features(feature_constraints),
    )
    
    return [
        {
            "changed_features": cf_row.diff_from_original,
            "magnitude": cf_row.magnitude,
            "predicted_outcome": cf_row.predicted_outcome,
            "humanized": humanize_cf(cf_row),
        }
        for cf_row in cf.cf_examples_list[0]
    ]

def humanize_cf(cf_row):
    """Convert raw cf to actionable Vietnamese sentence."""
    examples = []
    for feat, change in cf_row.diff_from_original.items():
        if feat == "focus_minutes":
            examples.append(f"tăng focus_minutes thêm {change:+.0f} phút/ngày")
        elif feat == "hint_count":
            examples.append(f"giảm hint_count xuống {change:+.0f}")
        # ...
    return f"Nếu bạn {' và '.join(examples)}, prediction sẽ thay đổi từ X → Y"
```

### 4. SAKT attention visualization

```python
# backend/explainability/attention_viz.py
def get_attention_weights(dkt_model, student_sequence):
    """Extract attention weights from SAKT for visualization.
    
    Grounded in: Pandey & Karypis 2019, attention as interpretability proxy.
    """
    with torch.no_grad():
        # Hook into transformer layers
        attentions = []
        def hook(module, input, output):
            attentions.append(output[1])  # (output, attention_weights)
        
        for layer in dkt_model.transformer.layers:
            layer.self_attn.register_forward_hook(hook)
        
        _ = dkt_model(student_sequence, query_concepts=...)
        
        # Aggregate across heads/layers
        return aggregate_attention(attentions)

def render_attention_for_student(student, concept_predicted):
    """Generate visualization data for student-facing UI."""
    attention = get_attention_weights(model, student.recent_sequence)
    
    # Find top 3 prior concepts that drove prediction
    top_3 = top_attended_concepts(attention[-1], n=3)
    
    return {
        "predicted_concept": concept_predicted.name,
        "top_drivers": [
            {
                "concept_name": c.name,
                "attention_weight": round(w, 3),
                "explanation": f"Bài tập về {c.name} bạn đã làm gần đây ảnh hưởng nhiều đến dự đoán này",
            }
            for c, w in top_3
        ],
    }
```

### 5. Tier endpoints

```python
# backend/explainability/views.py
class ExplainRiskMineView(APIView):
    """Student sees own simplified explanation."""
    permission_classes = [IsAuthenticated, IsStudent]
    
    def get(self, request):
        breakdown = compute_risk_score(request.user)
        explanation = explain_risk(breakdown, level="student")
        # Audit log
        log_explanation_request(request.user, "risk_score", level="student")
        return Response(explanation)


class ExplainRiskStudentView(APIView):
    """Lecturer sees technical explanation for assigned student."""
    permission_classes = [IsAuthenticated, IsLecturerOrAdmin, IsStudentInLecturerClass]
    
    def get(self, request, student_id):
        student = User.objects.get(pk=student_id)
        breakdown = compute_risk_score(student)
        explanation = explain_risk(breakdown, level="lecturer")
        log_explanation_request(request.user, "risk_score", level="lecturer", subject=student)
        return Response(explanation)
```

### 6. Frontend rendering

```typescript
// frontend/src/components/explainability/ExplanationPanel.tsx
function ExplanationPanel({ explanation, level }: Props) {
  if (level === "student") {
    return (
      <Card>
        <h3>Tại sao có dự đoán này?</h3>
        <Top3Factors factors={explanation.top_3_factors} />
        <CounterfactualSuggestion cf={explanation.counterfactual} />
        <p className="text-sm text-muted-foreground">
          Đây là giải thích đơn giản. Hỏi giảng viên nếu muốn chi tiết hơn.
        </p>
      </Card>
    );
  }
  
  // Lecturer view
  return (
    <Tabs>
      <Tab name="SHAP Waterfall"><SHAPWaterfall data={explanation.shap_waterfall} /></Tab>
      <Tab name="All Factors"><FullFactorTable data={explanation.all_factors} /></Tab>
      <Tab name="Counterfactuals"><CounterfactualTable data={explanation.counterfactuals} /></Tab>
      <Tab name="History"><ExplanationHistory data={explanation.history} /></Tab>
    </Tabs>
  );
}
```

## Compliance: GDPR Art.22 + NĐ 13/2023

Both regulations require:
- **Right to explanation** for automated decisions
- **Human review** option
- **Right to contest** the decision

PALP implementation:
- Every automated decision (RiskScore, DKT prediction, intervention suggestion) → `/api/explain/*` endpoint
- Lecturer dashboard "Override" button (human review path)
- "Báo cáo sai lệch" button → ticket to admin (contest path)

## Common pitfalls

- **Explanation doesn't match prediction**: bug — sanity check `sum(SHAP) + base ≈ prediction`
- **Counterfactual unactionable**: "If you had higher prior GPA" — useless. Filter to actionable features.
- **PII in explanation strings**: leak — use IDs, render names client-side
- **Slow inference**: cache nightly for top-N students
- **Same explanation for both audiences**: wasted opportunity — tier matters
- **No counterfactual diversity**: top 3 should be DIVERSE, not 3 variations of same factor (use DiCE diversity penalty)
- **Forgetting audit log**: compliance trail incomplete

## Performance budget

- SHAP for RiskScore (linear): < 50ms per student
- SAKT attention viz: < 200ms per student (cached)
- Counterfactual generation: < 1s (cache aggressively)
- Endpoint p95: < 500ms (cache hit), < 2s (cache miss)

## Test coverage

- Unit: SHAP values sum to prediction - baseline (within tolerance)
- Unit: counterfactual achieves predicted target change
- Integration: endpoint returns valid explanation per model
- Security: lecturer can't explain unassigned student
- Compliance: Art.22 challenge response within SLA

## Related

- [AI_COACH_ARCHITECTURE.md](../../../docs/AI_COACH_ARCHITECTURE.md) section 2 — XAI in governance layer
- [PRIVACY_V2_DPIA.md](../../../docs/PRIVACY_V2_DPIA.md) section 6 — Right to Explanation
- [model_cards/](../../../docs/model_cards/) — required Compliance section
- [risk-scoring skill](../risk-scoring/SKILL.md) — RiskScore explanation
- [dkt-engine skill](../dkt-engine/SKILL.md) — DKT attention explanation
- [SHAP library](https://github.com/shap/shap)
- [DiCE library](https://github.com/interpretml/DiCE)
