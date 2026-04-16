"""
Data Cleaning Pipeline Validation (DC-01 to DC-06).

QA_STANDARD Section 6.4.
"""
import pytest
import numpy as np
import pandas as pd

from analytics.etl.imputation import classify_missing_mechanism, impute_missing_values
from analytics.etl.outliers import detect_outliers

pytestmark = pytest.mark.data_qa


# ---------------------------------------------------------------------------
# DC-01: Missing data detection — pipeline detects missing values
# ---------------------------------------------------------------------------


class TestDC01MissingDataDetection:

    def test_detects_all_missing_values(self):
        df = pd.DataFrame({
            "score": [80, np.nan, 70, np.nan, 90],
            "hours": [10, 20, np.nan, 40, 50],
            "name": ["A", "B", "C", "D", "E"],
        })
        _, report = impute_missing_values(df, numeric_columns=["score", "hours"])
        total_missing = sum(
            d["missing_count"]
            for d in report["column_details"].values()
        )
        assert total_missing == 3

    def test_no_missing_reports_zero(self):
        df = pd.DataFrame({
            "score": [80, 90, 70, 60, 50],
            "hours": [10, 20, 30, 40, 50],
        })
        _, report = impute_missing_values(df, numeric_columns=["score", "hours"])
        total_missing = sum(
            d["missing_count"]
            for d in report["column_details"].values()
        )
        assert total_missing == 0

    def test_all_missing_detected(self):
        df = pd.DataFrame({
            "score": [np.nan] * 10,
        })
        _, report = impute_missing_values(df, numeric_columns=["score"])
        details = report["column_details"]["score"]
        assert details["missing_count"] == 10
        assert details["missing_pct"] == 1.0


# ---------------------------------------------------------------------------
# DC-02: Missing data classification (MCAR/MAR/MNAR)
# ---------------------------------------------------------------------------


class TestDC02MissingClassification:

    def test_complete_data(self):
        series = pd.Series([1, 2, 3, 4, 5])
        assert classify_missing_mechanism(series) == "complete"

    def test_negligible_missing(self):
        values = list(range(100))
        values[50] = np.nan
        series = pd.Series(values)
        mechanism = classify_missing_mechanism(series)
        assert mechanism == "negligible"

    def test_mar_likely(self):
        values = [1.0] * 100
        for i in range(10):
            values[i] = np.nan
        series = pd.Series(values)
        mechanism = classify_missing_mechanism(series)
        assert mechanism == "MAR_likely"

    def test_mar_suspected(self):
        values = [1.0] * 100
        for i in range(30):
            values[i] = np.nan
        series = pd.Series(values)
        mechanism = classify_missing_mechanism(series)
        assert mechanism == "MAR_suspected"

    def test_mnar_suspected_high_missing(self):
        values = [1.0] * 100
        for i in range(60):
            values[i] = np.nan
        series = pd.Series(values)
        mechanism = classify_missing_mechanism(series)
        assert mechanism == "MNAR_suspected"

    def test_empty_series(self):
        series = pd.Series([], dtype=float)
        mechanism = classify_missing_mechanism(series)
        assert mechanism == "complete"


# ---------------------------------------------------------------------------
# DC-03: KNN imputation — imputed values in valid range
# ---------------------------------------------------------------------------


class TestDC03KNNImputation:

    def test_imputed_values_not_nan(self):
        rng = np.random.default_rng(42)
        data = rng.normal(50, 10, size=(50, 3))
        df = pd.DataFrame(data, columns=["a", "b", "c"])
        df.iloc[5, 0] = np.nan
        df.iloc[10, 1] = np.nan
        df.iloc[15, 2] = np.nan

        df_out, report = impute_missing_values(df, n_neighbors=3)
        assert df_out[["a", "b", "c"]].isna().sum().sum() == 0

    def test_imputed_values_in_reasonable_range(self):
        df = pd.DataFrame({
            "score": [70, 75, 80, np.nan, 85, 90, 72, 78],
        })
        df_out, _ = impute_missing_values(df, n_neighbors=3)
        imputed_val = df_out.iloc[3]["score"]
        assert 60 <= imputed_val <= 100

    def test_high_missing_excluded(self):
        values = [1.0] * 100
        for i in range(60):
            values[i] = np.nan
        df = pd.DataFrame({"col": values})
        _, report = impute_missing_values(df)
        assert "col" in report["columns_excluded"]

    def test_low_missing_imputed(self):
        values = [1.0] * 100
        values[0] = np.nan
        values[1] = np.nan
        df = pd.DataFrame({"col": values})
        _, report = impute_missing_values(df)
        assert "col" in report["columns_imputed"]

    def test_imputation_report_counts(self):
        df = pd.DataFrame({
            "a": [1, 2, np.nan, 4, 5, 6, 7, 8],
            "b": [10, np.nan, 30, 40, 50, 60, 70, 80],
        })
        _, report = impute_missing_values(df, n_neighbors=3)
        assert report["total_values_imputed"] == 2


# ---------------------------------------------------------------------------
# DC-04: Outlier screening — Z-score/IQR detects known outliers
# ---------------------------------------------------------------------------


class TestDC04OutlierScreening:

    def test_detects_extreme_outlier_zscore(self):
        df = pd.DataFrame({
            "score": [70, 72, 75, 78, 80, 82, 85, 200],
        })
        _, queue = detect_outliers(df, zscore_threshold=2.0)
        flagged_values = [e["value"] for e in queue]
        assert 200 in flagged_values

    def test_detects_extreme_outlier_iqr(self):
        df = pd.DataFrame({
            "hours": list(range(10, 20)) + [500],
        })
        _, queue = detect_outliers(df)
        flagged_values = [e["value"] for e in queue]
        assert 500.0 in flagged_values

    def test_clean_data_no_outliers(self):
        rng = np.random.default_rng(42)
        df = pd.DataFrame({
            "score": rng.normal(75, 5, size=100),
        })
        _, queue = detect_outliers(df)
        assert len(queue) <= 3

    def test_flagged_by_field_present(self):
        df = pd.DataFrame({
            "score": [10, 11, 12, 13, 14, 15, 200],
        })
        _, queue = detect_outliers(df, zscore_threshold=2.0)
        if queue:
            assert "flagged_by" in queue[0]
            assert len(queue[0]["flagged_by"]) > 0

    def test_true_positive_rate(self):
        normal = [50 + i * 0.5 for i in range(50)]
        known_outliers = [200, 300, -100, 500, 999]
        df = pd.DataFrame({"val": normal + known_outliers})

        _, queue = detect_outliers(df, zscore_threshold=2.5)
        flagged_values = {e["value"] for e in queue}
        detected = sum(1 for v in known_outliers if v in flagged_values)
        tp_rate = detected / len(known_outliers)
        assert tp_rate >= 0.80


# ---------------------------------------------------------------------------
# DC-05: Idempotency — run pipeline twice, same result
# ---------------------------------------------------------------------------


class TestDC05Idempotency:

    def test_imputation_idempotent(self):
        rng = np.random.default_rng(42)
        data = rng.normal(50, 10, size=(30, 3))
        df = pd.DataFrame(data, columns=["a", "b", "c"])
        df.iloc[5, 0] = np.nan
        df.iloc[10, 1] = np.nan

        df_run1, _ = impute_missing_values(df.copy(), n_neighbors=3)
        df_run2, _ = impute_missing_values(df.copy(), n_neighbors=3)

        pd.testing.assert_frame_equal(df_run1, df_run2)

    def test_outlier_detection_idempotent(self):
        rng = np.random.default_rng(42)
        df = pd.DataFrame({
            "score": list(rng.normal(75, 5, size=50)) + [200],
        })

        _, queue1 = detect_outliers(df.copy())
        _, queue2 = detect_outliers(df.copy())

        values1 = sorted(e["value"] for e in queue1)
        values2 = sorted(e["value"] for e in queue2)
        assert values1 == values2

    def test_classification_idempotent(self):
        values = [1.0] * 100
        for i in range(15):
            values[i] = np.nan
        series = pd.Series(values)

        m1 = classify_missing_mechanism(series)
        m2 = classify_missing_mechanism(series)
        assert m1 == m2


# ---------------------------------------------------------------------------
# DC-06: Data quality score >= 70% after cleaning
# ---------------------------------------------------------------------------


class TestDC06QualityScore:

    def test_clean_data_high_score(self):
        from scripts.etl_academic import compute_quality_score
        score = compute_quality_score(100, 0, 0)
        assert score >= 70

    def test_moderate_issues_still_passes(self):
        from scripts.etl_academic import compute_quality_score
        score = compute_quality_score(100, 5, 3)
        assert score >= 70

    def test_heavy_issues_fails_threshold(self):
        from scripts.etl_academic import compute_quality_score
        score = compute_quality_score(100, 40, 20)
        assert score < 70
