"""SHAP-lite + counterfactual unit tests."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from explainability.engines.counterfactual import generate_for_risk
from explainability.engines.shap_lite import explain_risk_snapshot


@dataclass
class _FakeSnapshot:
    composite: float
    dimensions: dict
    severity: str = "yellow"


class TestExplainRiskSnapshot:
    def test_baseline_zero_contribution_when_at_baseline(self, settings):
        settings.PALP_RISK_WEIGHTS = {"academic": 1.0}
        snap = _FakeSnapshot(composite=40.0, dimensions={"academic": 0.40})
        out = explain_risk_snapshot(snap)
        assert len(out.contributions) == 1
        assert out.contributions[0].contribution == pytest.approx(0.0, abs=1e-6)

    def test_high_dimension_pushes_score_up(self, settings):
        settings.PALP_RISK_WEIGHTS = {"academic": 1.0}
        snap = _FakeSnapshot(composite=80.0, dimensions={"academic": 0.80})
        out = explain_risk_snapshot(snap)
        # (0.80 - 0.40) * 1.0 * 100 = +40
        assert out.contributions[0].contribution == pytest.approx(40.0)
        assert "đẩy lên" in out.summary

    def test_low_dimension_pulls_score_down(self, settings):
        settings.PALP_RISK_WEIGHTS = {"academic": 1.0}
        snap = _FakeSnapshot(composite=10.0, dimensions={"academic": 0.10})
        out = explain_risk_snapshot(snap)
        assert out.contributions[0].contribution < 0
        assert "kéo xuống" in out.summary

    def test_ranks_by_absolute_contribution(self, settings):
        settings.PALP_RISK_WEIGHTS = {"academic": 0.5, "behavioral": 0.5}
        snap = _FakeSnapshot(
            composite=60.0,
            dimensions={"academic": 0.50, "behavioral": 0.90},
        )
        out = explain_risk_snapshot(snap)
        # behavioral has bigger |delta| so should rank 1.
        assert out.contributions[0].feature_key == "behavioral"
        assert out.contributions[0].rank == 1
        assert out.contributions[1].rank == 2


class TestGenerateForRisk:
    def test_no_counterfactuals_when_target_already_met(self, settings):
        settings.PALP_RISK_WEIGHTS = {"academic": 1.0}
        snap = _FakeSnapshot(composite=10.0, dimensions={"academic": 0.10})
        out = generate_for_risk(snap, target_composite=20.0)
        assert out == []

    def test_returns_actionable_hint(self, settings):
        settings.PALP_RISK_WEIGHTS = {"behavioral": 1.0}
        snap = _FakeSnapshot(composite=70.0, dimensions={"behavioral": 0.70})
        out = generate_for_risk(snap, target_composite=60.0)
        assert out
        assert "Pomodoro" in out[0].actionable_hint

    def test_orders_by_feasibility(self, settings):
        settings.PALP_RISK_WEIGHTS = {
            "academic": 0.5, "behavioral": 0.5,
        }
        snap = _FakeSnapshot(
            composite=80.0,
            dimensions={"academic": 0.80, "behavioral": 0.80},
        )
        out = generate_for_risk(snap, target_composite=70.0)
        # behavioral feasibility (0.85) > academic feasibility (0.30) so
        # the higher-feasibility option should come first.
        assert out[0].feature_key == "behavioral"
