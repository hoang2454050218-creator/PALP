import datetime as dt

import numpy as np
import pytest
from django.utils import timezone

from mlops.drift import (
    build_drift_report,
    detect_categorical_drift,
    detect_numeric_drift,
)
from mlops.models import DriftReport, ModelRegistry
from mlops.registry import register_model, register_version

pytestmark = pytest.mark.django_db


def _aware(year, month, day):
    return timezone.make_aware(dt.datetime(year, month, day))


@pytest.fixture
def model_version(admin_user):
    reg = register_model("drift-target", ModelRegistry.ModelType.RISK_SCORE, owner=admin_user)
    return register_version(reg, "1.0.0")


class TestNumericDrift:
    def test_no_drift_same_distribution(self):
        rng = np.random.default_rng(42)
        ref = rng.normal(0, 1, 200)
        cur = rng.normal(0, 1, 200)
        res = detect_numeric_drift(ref, cur)
        assert res["p_value"] is not None
        assert res["p_value"] > 0.01  # cannot reject identical distributions

    def test_drift_detected_shifted_distribution(self):
        rng = np.random.default_rng(42)
        ref = rng.normal(0, 1, 200)
        cur = rng.normal(2, 1, 200)
        res = detect_numeric_drift(ref, cur)
        assert res["p_value"] is not None
        assert res["p_value"] < 0.001
        assert res["drift_score"] > 0.99

    def test_skips_when_sample_too_small(self):
        res = detect_numeric_drift([1, 2], [3, 4])
        assert res["skipped"] == "insufficient_sample"


class TestCategoricalDrift:
    def test_no_drift_same_distribution(self):
        ref = ["a"] * 50 + ["b"] * 50
        cur = ["a"] * 48 + ["b"] * 52
        res = detect_categorical_drift(ref, cur)
        assert res["p_value"] is not None
        assert res["p_value"] > 0.5

    def test_drift_detected_inverted(self):
        ref = ["a"] * 80 + ["b"] * 20
        cur = ["a"] * 20 + ["b"] * 80
        res = detect_categorical_drift(ref, cur)
        assert res["p_value"] is not None
        assert res["p_value"] < 0.001


class TestBuildDriftReport:
    def test_creates_report_no_drift(self, model_version):
        rng = np.random.default_rng(7)
        ref = {"focus_minutes": {"kind": "numeric", "values": rng.normal(40, 5, 200).tolist()}}
        cur = {"focus_minutes": {"kind": "numeric", "values": rng.normal(40, 5, 200).tolist()}}
        report = build_drift_report(
            model_version=model_version,
            reference_features=ref,
            current_features=cur,
            window_start=_aware(2026, 4, 1),
            window_end=_aware(2026, 4, 8),
        )
        assert report.severity == DriftReport.Severity.NONE
        assert report.drift_detected is False

    def test_creates_report_critical_drift(self, model_version):
        rng = np.random.default_rng(7)
        ref = {"focus_minutes": {"kind": "numeric", "values": rng.normal(40, 5, 200).tolist()}}
        cur = {"focus_minutes": {"kind": "numeric", "values": rng.normal(80, 5, 200).tolist()}}
        report = build_drift_report(
            model_version=model_version,
            reference_features=ref,
            current_features=cur,
            window_start=_aware(2026, 4, 1),
            window_end=_aware(2026, 4, 8),
        )
        assert report.severity == DriftReport.Severity.CRITICAL
        assert report.drift_detected is True
        assert "focus_minutes" in report.feature_summary

    def test_handles_missing_current_feature(self, model_version):
        ref = {"focus_minutes": {"kind": "numeric", "values": list(range(100))}}
        cur = {}  # no overlap
        report = build_drift_report(
            model_version=model_version,
            reference_features=ref,
            current_features=cur,
            window_start=_aware(2026, 4, 1),
            window_end=_aware(2026, 4, 8),
        )
        assert report.feature_summary["focus_minutes"]["skipped"] == "no_current_window"
