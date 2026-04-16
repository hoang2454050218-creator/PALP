import hashlib
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from django.db import transaction
from django.utils import timezone

from analytics.models import ETLRun, DataQualityLog
from events.services import audit_log
from events.models import EventLog
from .validators import validate_schema, detect_duplicate_keys, SchemaValidationError
from .imputation import impute_missing_values
from .outliers import detect_outliers

logger = logging.getLogger("palp.etl")

DEFAULT_KEY_COLUMNS = ["student_id", "course_code", "semester"]


def compute_file_checksum(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_df_checksum(df: pd.DataFrame) -> str:
    h = hashlib.sha256()
    h.update(pd.util.hash_pandas_object(df).values.tobytes())
    return h.hexdigest()


def run_pipeline(
    input_path: str,
    semester: str,
    admin_user=None,
    n_neighbors: int = 5,
    zscore_threshold: float = 3.0,
    iqr_factor: float = 1.5,
    random_seed: int = 42,
    verify: bool = False,
) -> ETLRun:
    np.random.seed(random_seed)

    input_checksum = compute_file_checksum(input_path)

    etl_run = ETLRun.objects.create(
        input_file=input_path,
        semester=semester,
        input_checksum=input_checksum,
        input_version=f"{Path(input_path).name}@{input_checksum[:12]}",
        parameters={
            "n_neighbors": n_neighbors,
            "zscore_threshold": zscore_threshold,
            "iqr_factor": iqr_factor,
            "random_seed": random_seed,
        },
        random_seed=random_seed,
    )

    if admin_user:
        audit_log(
            admin_user,
            EventLog.EventName.ETL_STARTED,
            {"run_id": str(etl_run.run_id), "input_file": input_path, "semester": semester},
        )

    try:
        df = _stage_load(etl_run, input_path)
        schema_result = _stage_validate(etl_run, df)
        duplicates = _stage_dedup(etl_run, df)
        df_clean, imputation_report = _stage_impute(etl_run, df, n_neighbors)
        df_final, outlier_queue = _stage_outliers(etl_run, df_clean, zscore_threshold, iqr_factor)
        _stage_import(etl_run, df_final, semester, admin_user)

        output_checksum = compute_df_checksum(df_final.drop(columns=["_outlier_flags"], errors="ignore"))
        etl_run.output_checksum = output_checksum
        etl_run.output_version = f"clean@{output_checksum[:12]}"
        etl_run.status = ETLRun.RunStatus.SUCCESS
        etl_run.completed_at = timezone.now()
        etl_run.report = {
            "schema": schema_result,
            "duplicates_count": len(duplicates),
            "imputation": imputation_report,
            "outliers_count": len(outlier_queue),
        }
        etl_run.save()

        DataQualityLog.objects.create(
            source=input_path,
            total_records=etl_run.total_records,
            missing_values=etl_run.missing_values_handled,
            outliers_detected=etl_run.outliers_flagged,
            records_cleaned=etl_run.records_imported,
            quality_score=_compute_quality_score(etl_run),
            details=etl_run.report,
        )

        if admin_user:
            audit_log(
                admin_user,
                EventLog.EventName.ETL_COMPLETED,
                {
                    "run_id": str(etl_run.run_id),
                    "records_imported": etl_run.records_imported,
                    "output_checksum": output_checksum,
                },
            )

    except SchemaValidationError as e:
        etl_run.status = ETLRun.RunStatus.FAILED
        etl_run.error_message = str(e)
        etl_run.report = {"schema_errors": e.errors}
        etl_run.completed_at = timezone.now()
        etl_run.save()
        _audit_failure(admin_user, etl_run, str(e))
        raise

    except Exception as e:
        etl_run.status = ETLRun.RunStatus.FAILED
        etl_run.error_message = str(e)
        etl_run.completed_at = timezone.now()
        etl_run.save()
        _audit_failure(admin_user, etl_run, str(e))
        raise

    return etl_run


def _stage_load(etl_run, input_path):
    logger.info("[ETL %s] Stage 1: Loading %s", etl_run.run_id, input_path)
    df = pd.read_csv(input_path)
    etl_run.total_records = len(df)
    etl_run.save(update_fields=["total_records"])
    return df


def _stage_validate(etl_run, df):
    logger.info("[ETL %s] Stage 2: Schema validation", etl_run.run_id)
    result = validate_schema(df)
    etl_run.schema_snapshot = result["snapshot"]
    etl_run.save(update_fields=["schema_snapshot"])
    return result


def _stage_dedup(etl_run, df):
    logger.info("[ETL %s] Stage 3: Duplicate key detection", etl_run.run_id)
    duplicates = detect_duplicate_keys(df, DEFAULT_KEY_COLUMNS)
    etl_run.duplicates_found = len(duplicates)
    etl_run.save(update_fields=["duplicates_found"])

    if not duplicates.empty:
        logger.warning(
            "[ETL %s] Found %d duplicate rows by key %s",
            etl_run.run_id, len(duplicates), DEFAULT_KEY_COLUMNS,
        )
    return duplicates


def _stage_impute(etl_run, df, n_neighbors):
    logger.info("[ETL %s] Stage 4: KNN imputation", etl_run.run_id)
    df_clean, report = impute_missing_values(df, n_neighbors=n_neighbors)
    etl_run.missing_values_handled = report["total_values_imputed"]
    etl_run.columns_excluded = report["columns_excluded"]
    etl_run.save(update_fields=["missing_values_handled", "columns_excluded"])
    return df_clean, report


def _stage_outliers(etl_run, df, zscore_threshold, iqr_factor):
    logger.info("[ETL %s] Stage 5: Outlier detection", etl_run.run_id)
    df_flagged, queue = detect_outliers(
        df,
        zscore_threshold=zscore_threshold,
        iqr_factor=iqr_factor,
    )
    etl_run.outliers_flagged = len(queue)
    etl_run.outlier_review_queue = queue
    etl_run.save(update_fields=["outliers_flagged", "outlier_review_queue"])
    return df_flagged, queue


def _stage_import(etl_run, df, semester, admin_user):
    logger.info("[ETL %s] Stage 6: Atomic import to database", etl_run.run_id)

    imported = 0
    skipped = 0

    with transaction.atomic():
        for _, row in df.iterrows():
            try:
                _import_row(row, semester)
                imported += 1
            except Exception as e:
                skipped += 1
                logger.warning("[ETL %s] Row skip: %s", etl_run.run_id, e)

    etl_run.records_imported = imported
    etl_run.records_skipped = skipped
    etl_run.save(update_fields=["records_imported", "records_skipped"])


def _import_row(row, semester):
    pass


def _compute_quality_score(etl_run):
    total = etl_run.total_records or 1
    missing_penalty = min(etl_run.missing_values_handled / total * 100, 50)
    outlier_penalty = min(etl_run.outliers_flagged / total * 50, 30)
    dup_penalty = min(etl_run.duplicates_found / total * 50, 20)
    return max(0, round(100 - missing_penalty - outlier_penalty - dup_penalty, 1))


def _audit_failure(admin_user, etl_run, error_msg):
    if admin_user:
        audit_log(
            admin_user,
            EventLog.EventName.ETL_FAILED,
            {"run_id": str(etl_run.run_id), "error": error_msg[:500]},
        )
