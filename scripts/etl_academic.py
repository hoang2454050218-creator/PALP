"""
ETL script for importing academic data from university systems.

Usage:
  python manage.py shell -c "exec(open('../scripts/etl_academic.py').read())"

Or standalone (with Django settings):
  DJANGO_SETTINGS_MODULE=palp.settings.development python etl_academic.py --input data.csv --semester 2025-2

This script delegates to the analytics.etl pipeline which handles:
  1. Schema validation (reject bad input)
  2. Duplicate key detection
  3. KNN imputation (columns <50% missing; >50% excluded)
  4. Outlier detection (Z-score + IQR) -- flagged, not dropped
  5. Atomic database import (all-or-nothing)
  6. Full run tracking (run_id, checksums, reproducibility)

Backward-compat helpers (`classify_missing_data`, `detect_outliers_zscore`,
`detect_outliers_iqr`, `compute_quality_score`) are exposed for legacy tests
that predate the move to ``backend/analytics/etl/*``.
"""
import argparse
import logging
import os
import sys

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("palp.etl")


def main():
    parser = argparse.ArgumentParser(description="PALP Academic Data ETL")
    parser.add_argument("--input", required=True, help="Input CSV file path")
    parser.add_argument("--semester", required=True, help="Semester code (e.g., 2025-2)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--verify", action="store_true", help="Re-run and verify checksum matches")
    args = parser.parse_args()

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "palp.settings.development")

    import django
    django.setup()

    from analytics.etl.pipeline import run_pipeline

    etl_run = run_pipeline(
        input_path=args.input,
        semester=args.semester,
        random_seed=args.seed,
        verify=args.verify,
    )

    logger.info("ETL run completed: %s", etl_run.run_id)
    logger.info("  Status:  %s", etl_run.status)
    logger.info("  Records: %d imported, %d skipped", etl_run.records_imported, etl_run.records_skipped)
    logger.info("  Missing values handled: %d", etl_run.missing_values_handled)
    logger.info("  Outliers flagged: %d", etl_run.outliers_flagged)
    logger.info("  Duplicates found: %d", etl_run.duplicates_found)
    logger.info("  Output checksum: %s", etl_run.output_checksum)


def classify_missing_data(column) -> str:
    """Backward-compat 4-tier classifier preserved for legacy ETL tests.

    Tier boundaries differ slightly from the new
    ``classify_missing_mechanism`` (which adds a 5th ``MAR_suspected`` band):
    legacy buckets are complete / negligible / MAR_likely / MNAR_suspected
    with the MAR→MNAR cutoff at 20%.
    """
    total = len(column)
    if total == 0:
        return "complete"
    na_count = column.isna().sum()
    pct = na_count / total
    if pct == 0:
        return "complete"
    if pct < 0.05:
        return "negligible"
    if pct < 0.20:
        return "MAR_likely"
    return "MNAR_suspected"


def detect_outliers_zscore(data, threshold: float = 3.0) -> list[int]:
    """Return positional indices of values whose |z-score| > threshold.

    Default threshold matches ``analytics.etl.outliers._detect_zscore`` (3.0
    sigma) so behaviour is consistent across the codebase. Pass an explicit
    ``threshold=2.0`` for noisier datasets where you want higher sensitivity.
    """
    arr = np.asarray(data, dtype=float)
    if arr.size < 3:
        return []
    std = arr.std()
    if std == 0:
        return []
    z = np.abs((arr - arr.mean()) / std)
    return [int(i) for i in np.where(z > threshold)[0]]


def detect_outliers_iqr(data, factor: float = 1.5) -> list[int]:
    """Return positional indices of IQR outliers.

    When IQR is zero (mostly identical values, common for sparse academic
    datasets) fall back to "anything different from the median" so genuine
    extremes still surface instead of being silently dropped.
    """
    arr = np.asarray(data, dtype=float)
    if arr.size < 4:
        return []
    q1 = np.quantile(arr, 0.25)
    q3 = np.quantile(arr, 0.75)
    iqr = q3 - q1
    if iqr == 0:
        median = np.median(arr)
        return [int(i) for i in np.where(arr != median)[0]]
    lower, upper = q1 - factor * iqr, q3 + factor * iqr
    return [int(i) for i in np.where((arr < lower) | (arr > upper))[0]]


def compute_quality_score(total_records: int, missing: int, outliers: int) -> float:
    """Pure-function quality scoring (0-100) used by legacy tests.

    Penalty model matches ``analytics.etl.pipeline._compute_quality_score`` but
    works on raw counts instead of an ``ETLRun`` instance.
    """
    if total_records <= 0:
        return 0
    missing_penalty = min(missing / total_records * 100, 50)
    outlier_penalty = min(outliers / total_records * 50, 30)
    return max(0, round(100 - missing_penalty - outlier_penalty, 1))


if __name__ == "__main__":
    main()
