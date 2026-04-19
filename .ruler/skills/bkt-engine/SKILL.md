---
name: bkt-engine
description: Bayesian Knowledge Tracing engine invariants, parameters, and update workflow for the PALP adaptive learning system. Use when modifying backend/adaptive/engine.py, mastery state, BKT parameters, or pathway recommendations.
---

# BKT Engine — Mastery Tracking Skill

## When to use

- Editing `backend/adaptive/engine.py`, `models.py`, `serializers.py`
- Adding new BKT parameter, mastery state field, or pathway logic
- Investigating why a learner's mastery jumped or got stuck
- Adding test under `backend/adaptive/tests/`

## Default parameters (do NOT change without sign-off)

Defined in `backend/palp/settings/base.py`:

```python
PALP_BKT_DEFAULTS = {
    "P_L0": 0.3,         # prior probability of mastery
    "P_TRANSIT": 0.09,   # learning rate (no-mastery -> mastery)
    "P_GUESS": 0.25,     # P(correct | not mastered)
    "P_SLIP": 0.10,      # P(incorrect | mastered)
}
```

Per-concept overrides live in `Concept.bkt_params` (JSON field). Always merge with defaults.

## Hard invariants (assert these in every change)

1. `0 <= p <= 1` for every probability field (`P_L0`, `P_TRANSIT`, `P_GUESS`, `P_SLIP`, posterior `mastery_p`).
2. `P_GUESS + P_SLIP < 1` — otherwise the model degenerates (correct answer has lower mastery posterior than incorrect).
3. `P_TRANSIT >= 0` and typically `<= 0.3`.
4. Posterior monotonicity: `mastery_p` after correct answer must be `>= mastery_p` after incorrect answer for the same prior.
5. Idempotency: replaying the same event sequence produces the same final mastery (state is deterministic given history).

Add unit tests for each invariant when introducing a new parameter. Pattern:

```python
def test_bkt_invariant_guess_slip_bound(self):
    with pytest.raises(ValidationError):
        ConceptParameters(p_guess=0.6, p_slip=0.5).clean()
```

## Update equation (reference)

Posterior probability of mastery after observation `o` (correct/incorrect):

```
P(L_n | correct)   = (P_L_{n-1} * (1 - P_SLIP)) /
                     (P_L_{n-1} * (1 - P_SLIP) + (1 - P_L_{n-1}) * P_GUESS)
P(L_n | incorrect) = (P_L_{n-1} * P_SLIP) /
                     (P_L_{n-1} * P_SLIP + (1 - P_L_{n-1}) * (1 - P_GUESS))
P(L_{n+1})         = P(L_n | o) + (1 - P(L_n | o)) * P_TRANSIT
```

Implemented in `backend/adaptive/engine.py::update_mastery()`. Do not duplicate — call the function.

## Workflow when editing

1. Read `backend/adaptive/engine.py`, `backend/adaptive/models.py::MasteryState`, `backend/adaptive/serializers.py`.
2. Add validation in serializer + model `clean()` if introducing new param.
3. Update `PALP_BKT_DEFAULTS` only with PO + ADR sign-off.
4. Run `pytest backend/adaptive/ -v` — all tests must pass.
5. Update `backend/adaptive/tests/test_adaptive_matrix.py` if new param affects pathway selection.
6. Emit `bkt_updated` event via `events.services.audit_log` if mastery changes by > 0.05.

## Common pitfalls

- Floating-point drift on long sequences — round to 4 decimals when serializing for API.
- Race condition on concurrent submissions — wrap mastery update in `transaction.atomic()` with `select_for_update()` on `MasteryState`.
- Forgetting to recompute pathway after mastery change — call `pathway.refresh_for_student(user_id)`.
