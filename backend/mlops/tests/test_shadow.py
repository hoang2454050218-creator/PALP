import datetime as dt
from django.utils import timezone

def _aware(year, month, day):
    return timezone.make_aware(dt.datetime(year, month, day))

import pytest

from mlops.models import ModelRegistry
from mlops.registry import register_model, register_version
from mlops.shadow import (
    collected_samples,
    reset_samples,
    shadow_predict,
    summarise,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def candidate_baseline(admin_user):
    reg = register_model("shadow-target", ModelRegistry.ModelType.RISK_SCORE, owner=admin_user)
    baseline = register_version(reg, "1.0.0")
    candidate = register_version(reg, "1.1.0")
    yield candidate, baseline
    reset_samples()


class TestShadowPredict:
    def test_returns_baseline_value(self, candidate_baseline):
        candidate, baseline = candidate_baseline
        result = shadow_predict(
            candidate, baseline,
            candidate_fn=lambda: 0.7,
            baseline_fn=lambda: 0.6,
        )
        assert result == 0.6  # caller sees baseline only

    def test_records_both_predictions(self, candidate_baseline):
        candidate, baseline = candidate_baseline
        shadow_predict(
            candidate, baseline,
            candidate_fn=lambda: 0.7,
            baseline_fn=lambda: 0.6,
        )
        samples = list(collected_samples(candidate, baseline))
        assert len(samples) == 1
        assert samples[0].candidate_pred == 0.7
        assert samples[0].baseline_pred == 0.6

    def test_candidate_exception_logs_nan_not_crash(self, candidate_baseline):
        candidate, baseline = candidate_baseline
        result = shadow_predict(
            candidate, baseline,
            candidate_fn=lambda: 1 / 0,
            baseline_fn=lambda: 0.5,
        )
        assert result == 0.5
        samples = list(collected_samples(candidate, baseline))
        assert len(samples) == 1


class TestSummarise:
    def test_empty_window_creates_record(self, candidate_baseline):
        candidate, baseline = candidate_baseline
        comp = summarise(
            candidate, baseline,
            window_start=_aware(2026, 4, 1),
            window_end=_aware(2026, 4, 8),
        )
        assert comp.n_predictions == 0
        assert comp.divergence_summary == {"empty_window": True}

    def test_perfect_agreement(self, candidate_baseline):
        candidate, baseline = candidate_baseline
        for _ in range(100):
            shadow_predict(candidate, baseline, candidate_fn=lambda: 0.5, baseline_fn=lambda: 0.5)
        comp = summarise(candidate, baseline, _aware(2026, 4, 1), _aware(2026, 4, 8))
        assert comp.n_predictions == 100
        assert comp.mean_abs_diff == 0.0
        assert comp.agreement_pct == 1.0

    def test_disagreement_outside_tolerance(self, candidate_baseline):
        candidate, baseline = candidate_baseline
        for _ in range(50):
            shadow_predict(candidate, baseline, candidate_fn=lambda: 0.9, baseline_fn=lambda: 0.4)
        comp = summarise(
            candidate, baseline,
            _aware(2026, 4, 1), _aware(2026, 4, 8),
            agreement_tolerance=0.05,
        )
        assert comp.n_predictions == 50
        assert comp.agreement_pct == 0.0
        assert abs(comp.mean_abs_diff - 0.5) < 1e-6

    def test_summarise_clears_buffer(self, candidate_baseline):
        candidate, baseline = candidate_baseline
        for _ in range(10):
            shadow_predict(candidate, baseline, candidate_fn=lambda: 0.5, baseline_fn=lambda: 0.5)
        summarise(candidate, baseline, _aware(2026, 4, 1), _aware(2026, 4, 8))
        assert list(collected_samples(candidate, baseline)) == []
