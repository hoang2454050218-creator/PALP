import numpy as np
import pytest

from causal.estimators import (
    cuped_ate,
    doubly_robust_ate,
    ipw_ate,
    naive_ate,
)


class TestNaiveATE:
    def test_no_effect(self):
        rng = np.random.default_rng(42)
        y = rng.normal(0, 1, 200)
        treatment = np.array([0] * 100 + [1] * 100)
        result = naive_ate(y, treatment)
        assert result["n_treatment"] == 100
        assert result["n_control"] == 100
        assert abs(result["ate"]) < 0.5  # noise but not far from 0

    def test_known_effect(self):
        rng = np.random.default_rng(42)
        y_ctrl = rng.normal(0, 1, 200)
        y_treat = rng.normal(0.5, 1, 200)
        y = np.concatenate([y_ctrl, y_treat])
        treatment = np.array([0] * 200 + [1] * 200)
        result = naive_ate(y, treatment)
        assert abs(result["ate"] - 0.5) < 0.2
        assert result["ate_ci_low"] is not None
        assert result["ate_ci_low"] < result["ate"] < result["ate_ci_high"]

    def test_empty_arm(self):
        result = naive_ate([1.0, 2.0, 3.0], [0, 0, 0])
        assert result["ate"] is None
        assert result["note"] == "empty_arm"


class TestCUPED:
    def test_variance_reduction_with_correlated_covariate(self):
        rng = np.random.default_rng(7)
        x = rng.normal(0, 1, 500)
        # y is partly explained by x + treatment effect
        treatment = np.array([0] * 250 + [1] * 250)
        y = x * 0.8 + treatment * 0.3 + rng.normal(0, 0.5, 500)

        result = cuped_ate(y, treatment, x)
        # ATE should still be ~0.3
        assert abs(result["ate"] - 0.3) < 0.1
        # CUPED should reduce variance noticeably
        assert result["variance_reduction"]["reduction_pct"] > 0.3

    def test_no_reduction_with_uncorrelated_covariate(self):
        rng = np.random.default_rng(7)
        x = rng.normal(0, 1, 500)
        y = rng.normal(0, 1, 500)  # independent of x
        treatment = np.array([0] * 250 + [1] * 250)
        result = cuped_ate(y, treatment, x)
        assert abs(result["variance_reduction"]["reduction_pct"]) < 0.05


class TestIPW:
    def test_known_effect_with_50pct_propensity(self):
        rng = np.random.default_rng(11)
        treatment = rng.binomial(1, 0.5, 1000)
        y = rng.normal(0, 1, 1000) + treatment * 1.0
        propensity = np.full(1000, 0.5)
        result = ipw_ate(y, treatment, propensity)
        assert abs(result["ate"] - 1.0) < 0.2

    def test_rejects_propensity_outside_open_interval(self):
        with pytest.raises(ValueError, match="positivity"):
            ipw_ate([1.0, 2.0], [1, 0], [0.0, 1.0])


class TestDoublyRobust:
    def test_correct_outcome_model_only(self):
        # Even with mis-specified propensity, correct outcome model -> good DR estimate.
        rng = np.random.default_rng(13)
        n = 1000
        treatment = rng.binomial(1, 0.5, n)
        y = treatment * 0.7 + rng.normal(0, 0.5, n)
        # Mu models are accurate
        mu_t = np.full(n, 0.7)
        mu_c = np.full(n, 0.0)
        # Propensity is wrong (we lie and say 0.7 everywhere)
        propensity = np.full(n, 0.7)
        result = doubly_robust_ate(y, treatment, propensity, mu_t, mu_c)
        assert abs(result["ate"] - 0.7) < 0.1

    def test_correct_propensity_only(self):
        rng = np.random.default_rng(17)
        n = 1000
        treatment = rng.binomial(1, 0.5, n)
        y = treatment * 0.7 + rng.normal(0, 0.5, n)
        # Propensity correct
        propensity = np.full(n, 0.5)
        # Outcome models wrong (constant zero)
        mu_t = np.zeros(n)
        mu_c = np.zeros(n)
        result = doubly_robust_ate(y, treatment, propensity, mu_t, mu_c)
        assert abs(result["ate"] - 0.7) < 0.15
