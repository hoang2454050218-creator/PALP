import pytest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts"))
from etl_academic import detect_outliers_zscore, detect_outliers_iqr, compute_quality_score

pytestmark = pytest.mark.data_qa


class TestQualityScore:

    def test_perfect_score(self):
        assert compute_quality_score(100, 0, 0) == 100

    def test_missing_values_reduce_score(self):
        score = compute_quality_score(100, 10, 0)
        assert score < 100

    def test_outliers_reduce_score(self):
        score = compute_quality_score(100, 0, 10)
        assert score < 100

    def test_both_penalties_applied(self):
        score = compute_quality_score(100, 10, 10)
        assert score < compute_quality_score(100, 10, 0)
        assert score < compute_quality_score(100, 0, 10)

    def test_zero_records_returns_zero(self):
        assert compute_quality_score(0, 0, 0) == 0

    def test_score_never_negative(self):
        score = compute_quality_score(10, 10, 10)
        assert score >= 0


class TestOutlierDetectionZScore:

    def test_clean_data_no_outliers(self):
        rng = np.random.default_rng(42)
        data = rng.normal(50, 5, size=100)
        outliers = detect_outliers_zscore(data)
        assert len(outliers) <= 2

    def test_extreme_value_detected(self):
        data = np.array([10, 11, 12, 13, 14, 15, 100])
        outliers = detect_outliers_zscore(data, threshold=2.0)
        assert len(outliers) >= 1

    def test_too_few_values_returns_empty(self):
        assert detect_outliers_zscore(np.array([1, 2])) == []

    def test_zero_std_returns_empty(self):
        assert detect_outliers_zscore(np.array([5, 5, 5, 5])) == []


class TestOutlierDetectionIQR:

    def test_clean_uniform_no_outliers(self):
        data = np.arange(1, 101, dtype=float)
        outliers = detect_outliers_iqr(data)
        assert len(outliers) == 0

    def test_extreme_value_detected(self):
        data = np.array([10, 11, 12, 13, 14, 15, 200])
        outliers = detect_outliers_iqr(data)
        assert len(outliers) >= 1
