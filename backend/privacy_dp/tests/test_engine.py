"""DP engine tests — Laplace + budget enforcement."""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pytest

from privacy_dp.engine import (
    BudgetExceededError,
    add_laplace_noise,
    spend,
)
from privacy_dp.models import EpsilonBudget


pytestmark = pytest.mark.django_db


class TestAddLaplaceNoise:
    def test_noise_is_zero_centered(self):
        rng = np.random.default_rng(0)
        samples = [
            add_laplace_noise(raw_value=10.0, sensitivity=1.0, epsilon=1.0, rng=rng) - 10.0
            for _ in range(2000)
        ]
        assert abs(float(np.mean(samples))) < 0.1

    def test_higher_epsilon_means_less_noise(self):
        rng = np.random.default_rng(7)
        scale_low_eps = [
            add_laplace_noise(raw_value=0, sensitivity=1.0, epsilon=0.1, rng=rng)
            for _ in range(2000)
        ]
        scale_high_eps = [
            add_laplace_noise(raw_value=0, sensitivity=1.0, epsilon=10.0, rng=rng)
            for _ in range(2000)
        ]
        assert float(np.std(scale_low_eps)) > float(np.std(scale_high_eps))

    def test_invalid_epsilon_raises(self):
        with pytest.raises(ValueError):
            add_laplace_noise(raw_value=0, sensitivity=1.0, epsilon=0)

    def test_invalid_sensitivity_raises(self):
        with pytest.raises(ValueError):
            add_laplace_noise(raw_value=0, sensitivity=-1, epsilon=1)


class TestSpend:
    def _make_budget(self, total: float = 1.0) -> EpsilonBudget:
        return EpsilonBudget.objects.create(
            scope="test_scope",
            period_start=date.today(),
            period_end=date.today() + timedelta(days=7),
            epsilon_total=total,
        )

    def test_spend_increments_budget(self):
        budget = self._make_budget(total=1.0)
        result, log = spend(
            scope=budget.scope,
            period_start=budget.period_start,
            epsilon=0.3,
            raw_value=42.0,
            query_kind="count",
            rng=np.random.default_rng(1),
        )
        budget.refresh_from_db()
        assert budget.epsilon_spent == pytest.approx(0.3)
        assert log.raw_value == pytest.approx(42.0)

    def test_overspend_raises(self):
        budget = self._make_budget(total=0.5)
        with pytest.raises(BudgetExceededError):
            spend(
                scope=budget.scope,
                period_start=budget.period_start,
                epsilon=0.6,
                raw_value=1.0,
            )

    def test_no_budget_raises(self):
        with pytest.raises(BudgetExceededError):
            spend(
                scope="missing",
                period_start=date.today(),
                epsilon=0.1,
                raw_value=1.0,
            )

    def test_view_lecturer_can_list(self, lecturer_api):
        budget = self._make_budget()
        spend(
            scope=budget.scope, period_start=budget.period_start,
            epsilon=0.2, raw_value=100.0,
            rng=np.random.default_rng(0),
        )
        resp_b = lecturer_api.get("/api/privacy-dp/budgets/")
        resp_q = lecturer_api.get("/api/privacy-dp/queries/")
        assert resp_b.status_code == 200
        assert resp_q.status_code == 200
        assert any(b["scope"] == budget.scope for b in resp_b.data["budgets"])
        assert resp_q.data["queries"]

    def test_view_student_blocked(self, student_api):
        resp = student_api.get("/api/privacy-dp/budgets/")
        assert resp.status_code == 403
