import sys
import os

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts")
)

import numpy as np

from etl_academic import (
    classify_missing_data,
    detect_outliers_zscore,
    detect_outliers_iqr,
    compute_quality_score,
)


class _NaResult:
    def __init__(self, count):
        self._count = count

    def sum(self):
        return self._count


class MockColumn:
    """Mimics a pandas Series for classify_missing_data."""

    def __init__(self, total, na_count):
        self._total = total
        self._na_count = na_count

    def isna(self):
        return _NaResult(self._na_count)

    def __len__(self):
        return self._total


class TestClassifyMissingData:
    def test_complete(self):
        col = MockColumn(total=100, na_count=0)
        assert classify_missing_data(col) == "complete"

    def test_negligible(self):
        col = MockColumn(total=100, na_count=3)
        assert classify_missing_data(col) == "negligible"

    def test_mar_likely(self):
        col = MockColumn(total=100, na_count=10)
        assert classify_missing_data(col) == "MAR_likely"

    def test_mnar_suspected(self):
        col = MockColumn(total=100, na_count=25)
        assert classify_missing_data(col) == "MNAR_suspected"

    def test_boundary_five_percent_is_mar(self):
        col = MockColumn(total=100, na_count=5)
        assert classify_missing_data(col) == "MAR_likely"

    def test_boundary_twenty_percent_is_mnar(self):
        col = MockColumn(total=100, na_count=20)
        assert classify_missing_data(col) == "MNAR_suspected"


class TestDetectOutliersZScore:
    def test_normal_data_no_outliers(self):
        data = np.array([10.0, 12.0, 11.0, 13.0, 10.0, 12.0, 11.0])
        assert detect_outliers_zscore(data) == []

    def test_extreme_value_detected(self):
        data = np.array([10, 12, 11, 13, 10, 12, 11, 100])
        outliers = detect_outliers_zscore(data)
        assert len(outliers) > 0
        assert 7 in outliers

    def test_too_few_values_returns_empty(self):
        data = np.array([1, 2])
        assert detect_outliers_zscore(data) == []

    def test_constant_values_returns_empty(self):
        data = np.array([5, 5, 5, 5, 5])
        assert detect_outliers_zscore(data) == []


class TestDetectOutliersIQR:
    def test_normal_data_no_outliers(self):
        data = np.array([10.0, 12.0, 11.0, 13.0, 10.0, 12.0, 11.0])
        assert detect_outliers_iqr(data) == []

    def test_extreme_value_detected(self):
        data = np.array([10, 12, 11, 13, 10, 12, 11, 100])
        outliers = detect_outliers_iqr(data)
        assert len(outliers) > 0

    def test_symmetric_outliers(self):
        data = np.array([50, 50, 50, 50, 50, 50, 50, 50, 0, 100])
        outliers = detect_outliers_iqr(data)
        assert len(outliers) >= 2


class TestComputeQualityScore:
    def test_perfect_score(self):
        assert compute_quality_score(100, 0, 0) == 100

    def test_missing_reduces_score(self):
        score = compute_quality_score(100, 10, 0)
        assert 0 < score < 100

    def test_outliers_reduce_score(self):
        score = compute_quality_score(100, 0, 10)
        assert 0 < score < 100

    def test_both_penalties_stack(self):
        score = compute_quality_score(100, 10, 10)
        only_missing = compute_quality_score(100, 10, 0)
        only_outliers = compute_quality_score(100, 0, 10)
        assert score < only_missing
        assert score < only_outliers

    def test_zero_records_returns_zero(self):
        assert compute_quality_score(0, 0, 0) == 0

    def test_score_never_negative(self):
        score = compute_quality_score(10, 10, 10)
        assert score >= 0
