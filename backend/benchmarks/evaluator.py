"""Pure-NumPy benchmark evaluator.

Two reference predictors plus a SAKT-style adaptor over our DKT
engine. We deliberately keep this dependency-free so the test suite
runs on the CI image without sklearn / torch.

Predictors implemented:

* ``baseline_global`` — predicts the global positive rate. Sanity
  floor: a real model must beat this.
* ``baseline_per_concept`` — predicts the per-concept positive rate
  observed in the training split. This is the classic "majority
  class" baseline used in KT papers.
* ``logistic_per_concept`` — fits a one-feature (running mastery
  estimate) logistic regression per concept on the training split.
  Closed-form via gradient descent in pure NumPy. This is what we
  publish as the ``palp-logistic@v1`` model card baseline.
* ``palp_dkt`` — wraps the existing ``dkt.engine.SAKTPredictor`` so
  third-party datasets and the production model are evaluated with
  exactly the same code path. No-op if the engine import fails (the
  evaluator simply skips that predictor and the run still records
  the rest of the metrics).

Metrics: AUC (via Mann-Whitney U), RMSE, accuracy at 0.5.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Sequence

import math
import numpy as np

from .loaders import Attempt


@dataclass
class EvaluationResult:
    metrics: Dict[str, float]
    sample_size: int


def _sigmoid(x: float | np.ndarray):
    return 1.0 / (1.0 + np.exp(-x))


def _train_test_split(
    attempts: Sequence[Attempt], train_ratio: float = 0.8
) -> tuple[List[Attempt], List[Attempt]]:
    if not attempts:
        return [], []
    cut = max(1, int(len(attempts) * train_ratio))
    return list(attempts[:cut]), list(attempts[cut:])


def _auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """Closed-form AUC via Mann-Whitney U. Returns 0.5 on edge cases."""
    pos_mask = y_true == 1
    n_pos = int(pos_mask.sum())
    n_neg = len(y_true) - n_pos
    if n_pos == 0 or n_neg == 0:
        return 0.5
    order = np.argsort(y_score, kind="mergesort")
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(y_score) + 1, dtype=float)
    rank_sum_pos = ranks[pos_mask].sum()
    auc = (rank_sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    return float(auc)


def _rmse(y_true: np.ndarray, y_score: np.ndarray) -> float:
    return float(math.sqrt(np.mean((y_true - y_score) ** 2)))


def _accuracy(y_true: np.ndarray, y_score: np.ndarray) -> float:
    return float(np.mean((y_score >= 0.5) == (y_true == 1)))


def _baseline_global(train: Sequence[Attempt], test: Sequence[Attempt]) -> np.ndarray:
    if not train:
        return np.full(len(test), 0.5)
    rate = float(np.mean([a.correct for a in train]))
    return np.full(len(test), rate)


def _baseline_per_concept(train: Sequence[Attempt], test: Sequence[Attempt]) -> np.ndarray:
    rates: dict[int, list[int]] = {}
    for a in train:
        rates.setdefault(a.concept_id, []).append(a.correct)
    out = np.zeros(len(test))
    fallback = float(np.mean([a.correct for a in train])) if train else 0.5
    for i, a in enumerate(test):
        bucket = rates.get(a.concept_id)
        out[i] = float(np.mean(bucket)) if bucket else fallback
    return out


def _logistic_per_concept(
    train: Sequence[Attempt],
    test: Sequence[Attempt],
    *,
    learning_rate: float = 0.1,
    epochs: int = 200,
    seed: int = 0,
) -> np.ndarray:
    """One-feature logistic regression per concept.

    Feature = trailing accuracy on this (student, concept) pair so
    far. Bias-only model where there is too little history. Trained
    with full-batch GD; epochs / lr chosen to converge well within
    a few hundred attempts in unit tests.
    """
    rng = np.random.default_rng(seed)
    by_concept: dict[int, list[tuple[float, int]]] = {}
    running: dict[tuple[int, int], list[int]] = {}

    for a in train:
        key = (a.student_id, a.concept_id)
        history = running.setdefault(key, [])
        feature = float(np.mean(history)) if history else 0.5
        by_concept.setdefault(a.concept_id, []).append((feature, a.correct))
        history.append(a.correct)

    weights: dict[int, tuple[float, float]] = {}
    for cid, samples in by_concept.items():
        x = np.array([s[0] for s in samples], dtype=float)
        y = np.array([s[1] for s in samples], dtype=float)
        if len(x) < 4 or float(y.std()) < 1e-6:
            weights[cid] = (0.0, math.log((y.mean() + 1e-3) / (1.0 - y.mean() + 1e-3)))
            continue
        w = float(rng.normal(0.0, 0.1))
        b = float(rng.normal(0.0, 0.1))
        for _ in range(epochs):
            preds = _sigmoid(w * x + b)
            grad_w = float(np.mean((preds - y) * x))
            grad_b = float(np.mean(preds - y))
            w -= learning_rate * grad_w
            b -= learning_rate * grad_b
        weights[cid] = (w, b)

    running_eval: dict[tuple[int, int], list[int]] = dict(running)
    out = np.zeros(len(test))
    fallback = float(np.mean([a.correct for a in train])) if train else 0.5
    for i, a in enumerate(test):
        key = (a.student_id, a.concept_id)
        history = running_eval.get(key, [])
        feature = float(np.mean(history)) if history else 0.5
        wb = weights.get(a.concept_id)
        if wb is None:
            out[i] = fallback
        else:
            w, b = wb
            out[i] = float(_sigmoid(w * feature + b))
        history.append(a.correct)
        running_eval[key] = history
    return np.clip(out, 1e-4, 1.0 - 1e-4)


def _palp_dkt(train: Sequence[Attempt], test: Sequence[Attempt]) -> np.ndarray | None:
    """Adaptor over our SAKT-style numpy DKT predictor.

    We import lazily so the benchmarks app can be imported in
    environments where ``dkt`` is unavailable (e.g. partial
    deployments). Returns ``None`` to signal "skip this predictor".
    """
    try:
        from dkt.engine import SAKTPredictor
    except Exception:
        return None

    concepts = sorted({a.concept_id for a in train} | {a.concept_id for a in test})
    if not concepts:
        return None
    predictor = SAKTPredictor(concept_ids=concepts, seed=42)

    history_per_student: dict[int, list[tuple[int, int]]] = {}
    for a in train:
        history_per_student.setdefault(a.student_id, []).append((a.concept_id, a.correct))

    out = np.zeros(len(test))
    for i, a in enumerate(test):
        history = history_per_student.get(a.student_id, [])
        try:
            prob = float(predictor.predict(history, target_concept_id=a.concept_id))
        except Exception:
            prob = 0.5
        out[i] = max(1e-4, min(1.0 - 1e-4, prob))
        history.append((a.concept_id, a.correct))
        history_per_student[a.student_id] = history
    return out


PREDICTORS: dict[str, Callable[[Sequence[Attempt], Sequence[Attempt]], np.ndarray | None]] = {
    "baseline_global": _baseline_global,
    "baseline_per_concept": _baseline_per_concept,
    "logistic_per_concept": _logistic_per_concept,
    "palp_dkt": _palp_dkt,
}


def evaluate(
    attempts: Sequence[Attempt],
    *,
    predictor: str,
    train_ratio: float = 0.8,
) -> EvaluationResult:
    """Run a single predictor on the given attempt stream.

    Returns ``EvaluationResult(metrics={}, sample_size=0)`` when the
    predictor opts out (e.g. DKT engine missing). Callers persist
    that as a "skipped" run.
    """
    if predictor not in PREDICTORS:
        raise ValueError(f"Unknown predictor '{predictor}'")
    train, test = _train_test_split(list(attempts), train_ratio=train_ratio)
    if not test:
        return EvaluationResult(metrics={}, sample_size=0)
    fn = PREDICTORS[predictor]
    scores = fn(train, test)
    if scores is None:
        return EvaluationResult(metrics={}, sample_size=0)
    y_true = np.array([a.correct for a in test], dtype=float)
    y_score = np.asarray(scores, dtype=float)
    metrics = {
        "auc": _auc(y_true, y_score),
        "rmse": _rmse(y_true, y_score),
        "accuracy": _accuracy(y_true, y_score),
    }
    return EvaluationResult(metrics=metrics, sample_size=len(test))
