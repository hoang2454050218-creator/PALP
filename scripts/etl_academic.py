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
"""
import os
import sys
import logging
import argparse

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


if __name__ == "__main__":
    main()
