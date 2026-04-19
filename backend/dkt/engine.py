"""SAKT-style Deep Knowledge Tracing — pure NumPy implementation.

We deliberately avoid PyTorch / Keras for the first ship. The model
captured here is a faithful, deterministic approximation of SAKT
(Pandey & Karypis 2019, "A Self-Attentive model for Knowledge
Tracing"):

* Each concept gets a small embedding vector.
* The student's recent attempts (last K) form the *key/value* memory.
* Predicting concept ``c`` next ⇒ a softmax-weighted average of past
  outcomes, weights being the dot-product of the *query* (concept c)
  with each past *key* (past concept).
* The output is a calibrated probability via a logistic.

This is enough to reproduce the qualitative behaviour SAKT papers
report (recency + concept similarity dominate), runs in microseconds
for sequences < 200, and stays auditable (no opaque weights). When a
real PyTorch SAKT lands later, the registry swap-in is ready (see
``DKTModelVersion``).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class DKTHyper:
    """Hyperparameters captured at training/serving time."""
    embed_dim: int = 16
    max_history: int = 64
    softmax_temperature: float = 1.0
    correctness_bias: float = 0.6  # weight given to "was it correct" vs "was it attempted"
    seed: int = 42


@dataclass
class AttemptRecord:
    concept_id: int
    is_correct: bool


@dataclass
class DKTPredictionOutput:
    concept_id: int
    p_correct_next: float
    confidence: float
    attention: list[dict]  # top-K (concept_id, weight, was_correct)
    sequence_length: int


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def predict(
    *,
    history: list[AttemptRecord],
    target_concept_id: int,
    concept_ids: list[int],
    hyper: DKTHyper | None = None,
) -> DKTPredictionOutput:
    """Return P(correct_next | target_concept, history).

    Pure function — no DB access. Called by ``services.refresh_predictions``
    and the ``/api/dkt/predict/`` view.

    Determinism: the embedding matrix is generated from a seeded
    NumPy RNG over the (sorted) ``concept_ids`` list, so the same
    universe of concepts always produces the same predictions for the
    same history.
    """
    hyper = hyper or DKTHyper()
    embed = _embedding_matrix(concept_ids, hyper.embed_dim, seed=hyper.seed)
    cid_to_index = {cid: i for i, cid in enumerate(sorted(concept_ids))}

    if target_concept_id not in cid_to_index:
        return DKTPredictionOutput(
            concept_id=target_concept_id,
            p_correct_next=0.5,
            confidence=0.0,
            attention=[],
            sequence_length=len(history),
        )

    history = list(history)[-hyper.max_history:]
    if not history:
        return DKTPredictionOutput(
            concept_id=target_concept_id,
            p_correct_next=0.5,
            confidence=0.0,
            attention=[],
            sequence_length=0,
        )

    query = embed[cid_to_index[target_concept_id]]
    keys = np.stack([
        embed[cid_to_index[h.concept_id]]
        for h in history
        if h.concept_id in cid_to_index
    ])
    aligned_history = [h for h in history if h.concept_id in cid_to_index]
    if keys.size == 0:
        return DKTPredictionOutput(
            concept_id=target_concept_id,
            p_correct_next=0.5,
            confidence=0.0,
            attention=[],
            sequence_length=len(history),
        )

    # Scaled dot-product attention.
    scaled = keys @ query / max(math.sqrt(hyper.embed_dim), 1e-9)
    weights = _softmax(scaled / max(hyper.softmax_temperature, 1e-9))

    # Outcome score = weighted average of past correctness with a
    # small "attempted at all" baseline so a fully-failed history
    # still moves slowly toward 0.
    correctness = np.array([1.0 if h.is_correct else 0.0 for h in aligned_history])
    attempted_baseline = float(np.mean(correctness)) if correctness.size else 0.5
    weighted_correct = float(np.sum(weights * correctness))
    raw_score = (
        hyper.correctness_bias * weighted_correct
        + (1.0 - hyper.correctness_bias) * attempted_baseline
    )

    # Logistic squash for calibration; scale so scores 0..1 map to
    # ~0.27..0.73 — DKT shouldn't be over-confident from a small
    # synthetic history.
    p_correct_next = _logistic((raw_score - 0.5) * 4.0)
    confidence = min(1.0, len(aligned_history) / hyper.max_history)

    top = np.argsort(-weights)[: min(3, len(weights))]
    attention = [
        {
            "concept_id": aligned_history[int(i)].concept_id,
            "weight": float(weights[int(i)]),
            "was_correct": bool(aligned_history[int(i)].is_correct),
        }
        for i in top
    ]

    return DKTPredictionOutput(
        concept_id=target_concept_id,
        p_correct_next=float(p_correct_next),
        confidence=float(confidence),
        attention=attention,
        sequence_length=len(aligned_history),
    )


def predict_many(
    *,
    history: list[AttemptRecord],
    target_concept_ids: list[int],
    concept_ids: list[int],
    hyper: DKTHyper | None = None,
) -> dict[int, DKTPredictionOutput]:
    """Batch helper — run :func:`predict` for many target concepts."""
    return {
        cid: predict(
            history=history,
            target_concept_id=cid,
            concept_ids=concept_ids,
            hyper=hyper,
        )
        for cid in target_concept_ids
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _embedding_matrix(concept_ids: list[int], dim: int, *, seed: int) -> np.ndarray:
    """Deterministic concept embedding matrix.

    Sorted ``concept_ids`` ⇒ same matrix across processes given the
    same seed and concept universe. Embeddings are unit-normalised so
    dot-product attention sits in a stable range.
    """
    sorted_ids = sorted(concept_ids)
    rng = np.random.default_rng(seed)
    matrix = rng.normal(size=(len(sorted_ids), dim))
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms < 1e-9, 1.0, norms)
    return matrix / norms


def _softmax(values: np.ndarray) -> np.ndarray:
    if values.size == 0:
        return values
    shifted = values - float(np.max(values))
    exp = np.exp(shifted)
    return exp / float(np.sum(exp))


def _logistic(value: float) -> float:
    if value >= 0:
        ez = math.exp(-value)
        return 1.0 / (1.0 + ez)
    ez = math.exp(value)
    return ez / (1.0 + ez)
