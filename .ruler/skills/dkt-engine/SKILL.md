---
name: dkt-engine
description: Deep Knowledge Tracing (SAKT/AKT transformer) — replaces BKT v2 for mastery prediction. Use when modifying backend/dkt/, training/inference, KG embedding, shadow deployment vs BKT.
---

# DKT Engine — SAKT/AKT Workflow

## When to use

- Editing `backend/dkt/` (network, trainer, inference, shadow, feature_flag)
- Hyperparameter tuning DKT model
- Retraining (weekly Celery task)
- Shadow deployment vs BKT v2 comparison
- Cutover decision (gradual rollout per cohort via feature flag)
- Investigating prediction error
- Adding KG concept embedding (P5B integration)
- Reviewing PR touching DKT code

## Hard invariants

1. **Causal validation before cutover** — uplift estimator (P0) shows ≥15% AUC improvement, per [causal-experiment skill](../causal-experiment/SKILL.md). Not just correlational benchmark.
2. **DP training mandatory** at production scale — Opacus DP-SGD with ε ≤ 1.0 per training run.
3. **Shadow deployment** before cutover — run DKT alongside BKT v2 for ≥4 weeks, log both in MLflow.
4. **Feature flag gradual** — `dkt_enabled` per cohort, not class-level. Roll forward + back easily.
5. **Fairness audit** per [fairness-audit skill](../fairness-audit/SKILL.md) before each retraining release.
6. **Model Card** per training version, in [`docs/model_cards/dkt_sakt_vX.md`](../../../docs/model_cards/) — bumped each retrain.
7. **MLflow lineage** every training run logged.
8. **Don't replace BKT v2** — both run in production parallel; DKT becomes default after gate. BKT v2 stays as fallback.
9. **Inference cached** — predictions per (student, concept, day) cached 24h in Redis to avoid GPU cost spike.

## App structure

```
backend/dkt/
├── models.py             # DKTModelVersion, DKTPrediction
├── network.py            # PyTorch SAKT/AKT transformer
├── trainer.py            # weekly Celery train task
├── trainer_dp.py         # DP-protected training (Opacus)
├── inference.py          # batched inference, Redis cache
├── shadow.py             # vs BKT v2 comparison
├── feature_flag.py       # dkt_enabled per cohort
├── kg_embedding.py       # concept embedding from KG (P5B)
├── views.py              # /api/dkt/predict/, admin endpoints
└── tests/
```

## Architecture: SAKT (Self-Attentive KT)

Per [Pandey & Karypis 2019](https://arxiv.org/abs/1907.06837):

```python
# backend/dkt/network.py
import torch
import torch.nn as nn

class SAKT(nn.Module):
    """Self-Attentive Knowledge Tracing.
    
    Grounded in: Piech 2015 DKT, Pandey & Karypis 2019 SAKT.
    """
    def __init__(self, n_concepts, n_responses=2, d_model=128, n_heads=4, n_layers=2, dropout=0.1):
        super().__init__()
        self.concept_embedding = nn.Embedding(n_concepts + 1, d_model, padding_idx=0)
        self.interaction_embedding = nn.Embedding(n_concepts * n_responses + 1, d_model, padding_idx=0)
        self.position_embedding = nn.Embedding(MAX_SEQ_LEN, d_model)
        
        self.transformer = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(d_model=d_model, nhead=n_heads, dropout=dropout, batch_first=True),
            num_layers=n_layers,
        )
        
        self.predict_head = nn.Linear(d_model, 1)
    
    def forward(self, interactions, query_concepts):
        """
        interactions: [batch, seq_len] of (concept_id * 2 + response) tokens
        query_concepts: [batch, seq_len] of concept ids being asked about
        Returns: [batch, seq_len] mastery probability for query concepts
        """
        positions = torch.arange(interactions.size(1), device=interactions.device).unsqueeze(0)
        
        x = self.interaction_embedding(interactions) + self.position_embedding(positions)
        q = self.concept_embedding(query_concepts) + self.position_embedding(positions)
        
        # Causal mask (no peek future)
        mask = torch.triu(torch.ones(interactions.size(1), interactions.size(1)), diagonal=1).bool()
        
        # Transformer attends to past interactions
        attended = self.transformer(x, mask=mask, is_causal=True)
        
        # Predict for query
        combined = attended + q
        logits = self.predict_head(combined).squeeze(-1)
        return torch.sigmoid(logits)
```

## Training workflow

### 1. Data preparation

```python
# backend/dkt/data.py
def build_training_dataset(students, course):
    """Build interaction sequences for SAKT.
    
    Each row: (student_id, concept_id, is_correct, timestamp).
    Sequence per student, sorted by time, padded to MAX_SEQ_LEN.
    """
    sequences = []
    for student in students:
        attempts = TaskAttempt.objects.filter(
            student=student,
            task__concept__course=course,
        ).order_by("created_at")[:MAX_SEQ_LEN]
        
        seq = [(a.task.concept.id, int(a.is_correct)) for a in attempts]
        if len(seq) >= MIN_SEQ_LEN:
            sequences.append(seq)
    
    return sequences
```

### 2. Train with DP

```python
# backend/dkt/trainer_dp.py
from opacus import PrivacyEngine
import mlflow

@shared_task
def train_dkt_weekly():
    """Weekly DKT training task with DP guarantee."""
    
    with mlflow.start_run(experiment_id=settings.MLFLOW_DKT_EXPERIMENT_ID):
        mlflow.log_params({
            "model": "SAKT",
            "d_model": 128,
            "n_heads": 4,
            "n_layers": 2,
            "epsilon_target": 1.0,
        })
        
        sequences = build_training_dataset(active_students(), main_course())
        train_loader, val_loader = split_loaders(sequences, train_pct=0.8)
        
        model = SAKT(n_concepts=Concept.objects.count(), d_model=128, n_heads=4, n_layers=2)
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        criterion = nn.BCELoss()
        
        # DP wrapper
        privacy_engine = PrivacyEngine()
        model, optimizer, train_loader = privacy_engine.make_private(
            module=model,
            optimizer=optimizer,
            data_loader=train_loader,
            noise_multiplier=settings.PALP_DP["NOISE_MULTIPLIER"],
            max_grad_norm=settings.PALP_DP["MAX_GRAD_NORM"],
        )
        
        for epoch in range(EPOCHS):
            train_loss = train_epoch(model, optimizer, criterion, train_loader)
            val_auc = evaluate(model, val_loader)
            mlflow.log_metric("train_loss", train_loss, step=epoch)
            mlflow.log_metric("val_auc", val_auc, step=epoch)
        
        epsilon = privacy_engine.accountant.get_epsilon(delta=1e-5)
        if epsilon > settings.PALP_DP["EPSILON_BUDGET_PER_RUN"]:
            raise EpsilonBudgetExceeded(f"ε={epsilon}")
        
        mlflow.log_metric("epsilon_final", epsilon)
        
        # Fairness audit
        fairness_result = audit_model(model, val_loader, sensitive_features)
        mlflow.log_dict(fairness_result, "fairness_audit.json")
        
        if not fairness_result["passed"]:
            raise FairnessGateFailed(fairness_result)
        
        # Register version
        version = DKTModelVersion.objects.create(
            mlflow_run_id=mlflow.active_run().info.run_id,
            val_auc=val_auc,
            epsilon=epsilon,
            fairness_passed=True,
            status="shadow",  # not production yet
        )
        
        # Save model
        torch.save(model.state_dict(), f"models/dkt_v{version.id}.pt")
        mlflow.pytorch.log_model(model, "model")
```

### 3. Shadow deployment

```python
# backend/dkt/shadow.py
def predict_with_shadow(student, concept):
    """During shadow phase, predict with both BKT v2 (default) and DKT (shadow).
    Log both, return BKT v2.
    """
    bkt_prediction = backend.adaptive.engine.get_mastery_state(student, concept).p_mastery
    dkt_prediction = dkt_predict(student, concept)
    
    # Log to MLflow for comparison
    mlflow.log_metric("bkt_dkt_diff", abs(bkt_prediction - dkt_prediction))
    
    return bkt_prediction  # default during shadow
```

### 4. Feature flag cutover

```python
# backend/dkt/feature_flag.py
def get_active_predictor(student):
    """Decide BKT v2 or DKT based on cohort feature flag + model status."""
    cohort = student.peer_cohort
    
    if cohort and cohort.dkt_enabled:
        production_dkt = DKTModelVersion.objects.filter(status="production").latest("created_at")
        return DKTPredictor(production_dkt)
    
    return BKTPredictor()  # default
```

Roll out by enabling cohort flag gradually:
- Week 1: 5% cohorts
- Week 2: 25%
- Week 3: 50%
- Week 4: 100% if no regression

### 5. Cutover gate

Before flipping `dkt_enabled` widely:
- Causal A/B per [causal-experiment skill](../causal-experiment/SKILL.md): DKT uplift ≥ 15% AUC
- Fairness pass per [fairness-audit skill](../fairness-audit/SKILL.md)
- Latency check: DKT inference p95 < 200ms (with cache)
- Cost check: GPU cost projection within FinOps budget
- Rollback procedure tested

## KG integration (P5B)

Concept embedding from prerequisite graph:

```python
# backend/dkt/kg_embedding.py
def init_concept_embeddings_from_kg(model, concept_kg):
    """Initialize concept embeddings using KG structure (Node2Vec or GNN)."""
    embeddings = compute_node2vec(concept_kg, dim=128)
    
    with torch.no_grad():
        for concept_id, embedding in embeddings.items():
            model.concept_embedding.weight[concept_id] = torch.tensor(embedding)
```

This warm-starts SAKT with prerequisite-aware embeddings → faster convergence + better cold-start for new concepts.

## Inference

```python
# backend/dkt/inference.py
def dkt_predict(student, concept):
    """Cached batched inference."""
    cache_key = f"dkt:{student.id}:{concept.id}:{today_iso()}"
    cached = redis.get(cache_key)
    if cached:
        return float(cached)
    
    # Batch inference for performance
    interactions = build_interaction_sequence(student)
    query = torch.tensor([[concept.id]])
    
    model = load_production_dkt()
    with torch.no_grad():
        prediction = model(interactions, query).item()
    
    redis.setex(cache_key, 86400, prediction)  # 24h TTL
    
    DKTPrediction.objects.create(
        student=student,
        concept=concept,
        predicted_mastery=prediction,
        model_version=model_version,
    )
    
    return prediction
```

## Monitoring

Grafana dashboard `dkt-quality`:
- Inference latency p50/p95/p99
- Cache hit rate
- Shadow vs production diff distribution
- Per-cohort uplift over time
- Drift (input distribution vs training)

## Common pitfalls

- **No DP**: model memorizes individual student, vulnerable to inversion
- **Skipping shadow**: cutover regression hits production users
- **Class-level feature flag**: too coarse; some cohorts not ready
- **No fairness audit per retrain**: bias drift over time
- **Cold-start on new concepts**: KG embedding init mitigates
- **GPU cost not tracked**: FinOps surprise; profile inference cost per query
- **Cache miss storm after retrain**: pre-warm cache for active users

## Test coverage

- Unit: SAKT forward pass, attention mask correctness, embedding lookup
- Integration: end-to-end train + predict on synthetic data
- DP: epsilon stays under budget
- Fairness: synthetic biased data → audit catches
- Shadow: predictions logged to both
- Cutover: feature flag switch produces different result

## Related

- [LEARNING_SCIENCE_FOUNDATIONS.md](../../../docs/LEARNING_SCIENCE_FOUNDATIONS.md) section 2.1
- [DIFFERENTIAL_PRIVACY_SPEC.md](../../../docs/DIFFERENTIAL_PRIVACY_SPEC.md) section 3.1
- [model_cards/dkt_sakt_v1.md](../../../docs/model_cards/) — model card
- [bkt-engine skill](../bkt-engine/SKILL.md) — BKT v1/v2 baseline
- [causal-experiment skill](../causal-experiment/SKILL.md) — uplift validation
- [fairness-audit skill](../fairness-audit/SKILL.md)
- [xai-interpretation skill](../xai-interpretation/SKILL.md) — SAKT attention viz
