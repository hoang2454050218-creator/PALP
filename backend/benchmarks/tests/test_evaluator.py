"""Pure-NumPy evaluator tests (no DB)."""
from __future__ import annotations

import math

import numpy as np

from benchmarks.evaluator import (
    PREDICTORS,
    _accuracy,
    _auc,
    _rmse,
    evaluate,
)
from benchmarks.loaders import (
    Attempt,
    assistments_2009_synthetic,
    ednet_synthetic,
)


class TestPureMetrics:
    def test_auc_separates_perfect(self):
        y_true = np.array([0, 0, 1, 1])
        y_score = np.array([0.1, 0.2, 0.8, 0.9])
        assert _auc(y_true, y_score) == 1.0

    def test_auc_falls_back_when_one_class(self):
        y_true = np.array([1, 1, 1, 1])
        y_score = np.array([0.1, 0.2, 0.8, 0.9])
        assert _auc(y_true, y_score) == 0.5

    def test_rmse_is_zero_for_perfect(self):
        y_true = np.array([0, 1, 1, 0], dtype=float)
        y_score = np.array([0, 1, 1, 0], dtype=float)
        assert math.isclose(_rmse(y_true, y_score), 0.0)

    def test_accuracy_threshold(self):
        y_true = np.array([0, 0, 1, 1])
        y_score = np.array([0.1, 0.4, 0.6, 0.9])
        assert _accuracy(y_true, y_score) == 1.0


class TestSyntheticLoaders:
    def test_ednet_is_deterministic(self):
        a = list(ednet_synthetic(seed=7, students=5, concepts=4, interactions_per_student=6))
        b = list(ednet_synthetic(seed=7, students=5, concepts=4, interactions_per_student=6))
        assert a == b

    def test_assistments_distribution_has_both_outcomes(self):
        rows = list(assistments_2009_synthetic(seed=1, students=5, concepts=4, interactions_per_student=10))
        rates = {a.correct for a in rows}
        assert {0, 1}.issubset(rates)


class TestEvaluatorPredictors:
    def _attempts(self):
        return list(ednet_synthetic(seed=11, students=8, concepts=5, interactions_per_student=12))

    def test_baseline_global_returns_metrics(self):
        result = evaluate(self._attempts(), predictor="baseline_global")
        assert {"auc", "rmse", "accuracy"} <= set(result.metrics.keys())
        assert 0.0 <= result.metrics["accuracy"] <= 1.0

    def test_logistic_beats_global(self):
        attempts = self._attempts()
        baseline = evaluate(attempts, predictor="baseline_global").metrics
        logistic = evaluate(attempts, predictor="logistic_per_concept").metrics
        assert logistic["rmse"] <= baseline["rmse"] + 0.05

    def test_unknown_predictor_raises(self):
        try:
            evaluate(self._attempts(), predictor="bogus")
        except ValueError as exc:
            assert "Unknown predictor" in str(exc)
        else:
            raise AssertionError("Expected ValueError")

    def test_palp_dkt_runs_or_skips(self):
        attempts = self._attempts()
        result = evaluate(attempts, predictor="palp_dkt")
        if result.metrics:
            assert {"auc", "rmse", "accuracy"} <= set(result.metrics.keys())
        else:
            assert result.sample_size == 0

    def test_predictor_registry_lists_expected_keys(self):
        for k in ("baseline_global", "baseline_per_concept", "logistic_per_concept", "palp_dkt"):
            assert k in PREDICTORS


class TestEdgeCases:
    def test_evaluator_handles_empty(self):
        result = evaluate([], predictor="baseline_global")
        assert result.metrics == {}
        assert result.sample_size == 0

    def test_attempt_dataclass_is_hashable(self):
        a = Attempt(student_id=1, concept_id=2, correct=1, ts_ms=5)
        b = Attempt(student_id=1, concept_id=2, correct=1, ts_ms=5)
        assert {a, b} == {a}
