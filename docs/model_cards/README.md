# Model Cards

> Documentation chuẩn cho mọi ML model deploy trong PALP. Tuân thủ [Mitchell et al. 2019 "Model Cards for Model Reporting"](https://arxiv.org/abs/1810.03993) + [Gebru et al. 2018 "Datasheets for Datasets"](https://arxiv.org/abs/1803.09010).

## 1. Tại sao Model Cards

Mỗi ML model deploy vào production có thể impact 1000s sinh viên. Model Cards đảm bảo:

- **Transparency**: anyone (lecturer, sv, admin, regulator) có thể tra cứu intended use, limitations, fairness
- **Reproducibility**: training data + hyperparameters đầy đủ
- **Accountability**: owner + version + change history
- **Compliance**: GDPR Art.22, NĐ 13/2023 require explainability — Model Card là baseline

Without Model Cards, ML system là black box — không thể defend khi bị challenge legally hoặc ethically.

## 2. Khi nào tạo / update

| Event | Action |
|---|---|
| Train new model version | New card hoặc bump version trên existing card |
| Change hyperparameters | Bump version |
| Deploy to production | Card phải exist + reviewed + approved |
| Retrain on new data | Update training data section + bump version |
| Fairness audit fail | Document in card + retraining plan |
| Model deprecation | Mark deprecated + reason |

## 3. Folder structure

```
docs/model_cards/
├── README.md                          # this file
├── _template.md                       # template to copy
├── risk_score_v1.md                   # P1 RiskScore
├── bkt_v2_v1.md                       # P1 BKT v2
├── dkt_sakt_v1.md                     # P5 DKT/SAKT
├── survival_cox_v1.md                 # P5 Survival
├── bandit_thompson_v1.md              # P5 Contextual Bandit
├── herd_cluster_dbscan_v1.md          # P3 Herd Detection
├── jailbreak_classifier_v1.md         # P4 LLM Hardening
├── pii_ner_v1.md                      # P4 PII Guard NER
├── emergency_classifier_v1.md         # P4 Emergency Detection
├── affect_keystroke_v1.md             # P6D Keystroke
├── affect_linguistic_v1.md            # P6D Sentiment
└── affect_facial_v1.md                # P6D Facial (on-device)
```

## 4. Template (`_template.md`)

```markdown
# Model Card: {Model Name} v{X.Y.Z}

## Model Details

- **Model name**: 
- **Version**: 
- **Date**: YYYY-MM-DD
- **Owner**: @{team-member}
- **Type**: classifier / regressor / clustering / generative
- **Algorithm**: 
- **Framework**: PyTorch X.Y / scikit-learn X.Y / etc.
- **Lineage URL**: MLflow run URL

## Intended Use

### Primary intended uses

[Specifically what the model is FOR. Be concrete.]

### Primary intended users

[Who interacts with this model output. Student / Lecturer / Admin / System internal]

### Out-of-scope use cases

[What the model is NOT for. Be explicit. E.g., "Not for high-stakes decisions like grade assignment."]

## Factors

### Relevant factors

[What demographic / context factors might affect performance? E.g., gender, region, prior GPA, course type]

### Evaluation factors

[Which factors were evaluated for fairness?]

## Metrics

### Model performance measures

[Primary metric (e.g., AUC, F1, MAE) + value]
[Secondary metrics + values]

### Decision thresholds

[If classifier, what threshold? Why?]

### Variation approaches

[How were variations / errors measured? Cross-validation, holdout, bootstrap?]

## Evaluation Data

### Datasets

[Names, sources, sizes]

### Motivation

[Why these datasets?]

### Preprocessing

[Cleaning, normalization, augmentation]

## Training Data

### Datasets

[Same fields as Evaluation Data]

### Provenance

[Where data come from, when collected, how]

### Demographic distribution

| Attribute | Distribution |
|---|---|
| Gender | M: X%, F: Y%, Other: Z% |
| Region | (subgroups) |
| Year of study | (subgroups) |
| Prior GPA | (distribution) |

## Quantitative Analyses

### Unitary results

[Performance metric overall + per subgroup]

### Intersectional results

[Performance per intersection (e.g., gender × region)]

## Ethical Considerations

### Risks

[List risks. E.g., "Risk: model may underperform for low-data subgroups."]

### Mitigations

[Per risk, what mitigation in place]

### Data sensitivity

[What PII / sensitive data the model uses]

## Caveats and Recommendations

### Known limitations

[Be honest about what model can't do well]

### Recommendations for use

[How to use safely, what guardrails needed]

## Compliance

- **GDPR Art.22 explanation**: [Link to XAI explanation interface]
- **Vietnam NĐ 13/2023**: [Compliance status]
- **Fairness audit**: [Last audit date + result + report URL]
- **DPIA reference**: [PRIVACY_V2_DPIA.md section X]

## Update History

| Date | Version | Author | Change |
|---|---|---|---|
| YYYY-MM-DD | 1.0.0 | @user | Initial release |
```

## 5. Example: `risk_score_v1.md`

```markdown
# Model Card: RiskScore v1.0.0

## Model Details

- **Model name**: PALP RiskScore Composite Model
- **Version**: 1.0.0
- **Date**: 2026-06-01
- **Owner**: @ml-eng-1
- **Type**: regressor (output 0-100 composite score)
- **Algorithm**: Weighted linear combination of 5 dimensions (academic, behavioral, engagement, psychological, metacognitive)
- **Framework**: Plain Python (sklearn-compatible interface)
- **Lineage URL**: mlflow://palp/risk_score/runs/abc123

## Intended Use

### Primary intended uses

Identify students at risk of falling behind, for prioritizing lecturer intervention. Composite of 5 dimensions provides multi-faceted view rather than single-signal alert.

### Primary intended users

- **Lecturer**: see breakdown to plan intervention
- **Student**: see own composite score (not raw subscores) with counterfactual explanation
- **System**: input to PolicyService for nudge dispatch decision

### Out-of-scope use cases

- **NOT for grading or course outcome decisions** — score is signal, not verdict
- **NOT for admissions or academic standing** — based on behavioral/engagement, not achievement
- **NOT for cross-institution comparison** — calibrated per-institution

## Factors

### Relevant factors

- Year of study (Year 1 typically higher baseline risk due to transition)
- Course difficulty
- Class size
- Time of semester (mid-term spike)

### Evaluation factors

Fairness checked across: gender, region (urban/rural), economic band (where available), year of study.

## Metrics

### Model performance measures

- **Pearson correlation with end-of-semester GPA**: r = 0.42 (n = 1500, 95% CI [0.37, 0.47])
- **AUC for predicting "intervention needed" label**: 0.68
- **Calibration**: Brier score 0.18

### Decision thresholds

- Risk > 70: trigger lecturer alert
- Risk > 85: trigger urgent intervention
- Thresholds tunable in `PALP_RISK_WEIGHTS` settings

### Variation approaches

5-fold cross-validation; subgroup performance separately computed.

## Evaluation Data

### Datasets

PALP pilot data 2025-2026, 3 courses, n = 1500 students.

### Motivation

Validate against real-world outcome (GPA, intervention success).

### Preprocessing

Filter students với < 30 days activity (insufficient signal). Impute missing dimension with cohort mean.

## Training Data

### Datasets

Same as evaluation (regression coefficients fit on 80% train split).

### Provenance

Collected 2025-09-01 to 2026-05-31, with `behavioral_signals` consent. Stored encrypted, accessed via Feast feature store.

### Demographic distribution

| Attribute | Distribution |
|---|---|
| Gender | M: 60%, F: 40% (CS-heavy courses) |
| Region | Urban: 70%, Rural: 30% |
| Year | Year 1: 35%, Year 2: 30%, Year 3: 25%, Year 4: 10% |

## Quantitative Analyses

### Unitary results

- Overall AUC: 0.68

### Intersectional results

| Subgroup | AUC | Disparate impact ratio |
|---|---|---|
| M | 0.69 | 1.00 (baseline) |
| F | 0.66 | 0.96 |
| Urban | 0.69 | 1.00 |
| Rural | 0.65 | 0.94 |
| Year 1 | 0.71 | 1.03 |
| Year 4 | 0.62 | 0.90 |

All disparate impact ratios > 0.8 → fairness audit pass.

## Ethical Considerations

### Risks

- **Self-fulfilling prophecy**: lecturer treats high-risk student differently → outcome confirms label
- **Discriminatory triage**: if subgroup gets more interventions due to model bias

### Mitigations

- Self-fulfilling: lecturer training emphasizes growth mindset; intervention quality measured
- Discriminatory triage: fairness audit per release; quarterly review

### Data sensitivity

Indirect PII (behavioral patterns). Consent gate `behavioral_signals` enforced.

## Caveats and Recommendations

### Known limitations

- Cold start: low confidence in week 1-2 (insufficient data)
- Validity established only on Vietnamese higher-ed; cross-cultural unknown
- Behavioral signals can be gamed (sv aware → modify behavior)

### Recommendations for use

- Display with [XAI panel](../docs/AI_COACH_ARCHITECTURE.md) — never raw number alone
- Lecturer reviews evidence before intervention, not blindly trust
- Refresh weekly; don't carry old risk forward without recompute

## Compliance

- **GDPR Art.22 explanation**: Available at `/api/explain/risk/<id>/` (P6A XAI Layer)
- **Vietnam NĐ 13/2023**: Compliant — automated decision with human review + explanation
- **Fairness audit**: Last 2026-05-30, all subgroups pass; report at `mlflow://palp/fairness/risk_score_v1`
- **DPIA reference**: [PRIVACY_V2_DPIA.md](../PRIVACY_V2_DPIA.md) section 3.1, 3.2

## Update History

| Date | Version | Author | Change |
|---|---|---|---|
| 2026-06-01 | 1.0.0 | @ml-eng-1 | Initial release |
```

## 6. Datasheet for Datasets (Gebru 2018)

For each major training dataset, also create a Datasheet:

```
docs/model_cards/datasheets/
├── _datasheet_template.md
├── palp_pilot_2025_2026.md
├── ednet_riiid.md
├── assistments_2017.md
└── junyi_academy.md
```

Datasheet template covers:
- Motivation (why dataset exists)
- Composition (what's in it)
- Collection process
- Preprocessing/cleaning
- Uses (intended + out-of-scope)
- Distribution (license, format)
- Maintenance

Full template at [Gebru et al. 2018 datasheets paper](https://arxiv.org/abs/1803.09010).

## 7. Card review process

1. Author drafts card concurrent with model training
2. Peer reviewer (different team member) checks:
   - Performance numbers reproducible from MLflow
   - Fairness audit referenced + pass
   - Limitations honestly stated
   - Compliance fields completed
3. Owner approves
4. Card committed to repo (not just MLflow)
5. Update [`docs/model_cards/README.md`](README.md) index if new card

## 8. Public-facing version

For models that affect students directly (RiskScore, DKT, Bandit), publish simplified card on [`/(student)/about/models`](../../frontend/src/app/(student)/about/models/page.tsx):

- Name + purpose
- Plain language explanation
- "Last reviewed" date
- Fairness summary
- Link to full technical card (admin-accessible)

## 9. References

- [Mitchell et al. 2019 "Model Cards for Model Reporting"](https://arxiv.org/abs/1810.03993)
- [Gebru et al. 2018 "Datasheets for Datasets"](https://arxiv.org/abs/1803.09010)
- [Hugging Face Model Cards examples](https://huggingface.co/docs/hub/model-cards)
- [Google Model Card Toolkit](https://github.com/tensorflow/model-card-toolkit)

## 10. Related docs

- [AI_COACH_ARCHITECTURE.md](../AI_COACH_ARCHITECTURE.md) — list of all ML models
- [PRIVACY_V2_DPIA.md](../PRIVACY_V2_DPIA.md) — privacy assessment per model use
- [LEARNING_SCIENCE_FOUNDATIONS.md](../LEARNING_SCIENCE_FOUNDATIONS.md) — theory grounding
- [PUBLICATION_ROADMAP.md](../PUBLICATION_ROADMAP.md) — academic version of cards
- [fairness-audit skill](../../.ruler/skills/fairness-audit/SKILL.md)

## 11. Living document

Update khi:
- New model deployed → new card
- Mitchell/Gebru framework updated → migrate template
- Regulatory requirement adds field → add field
