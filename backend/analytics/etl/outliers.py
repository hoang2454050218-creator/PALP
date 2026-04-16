import logging
import numpy as np
import pandas as pd

logger = logging.getLogger("palp.etl")


def detect_outliers(
    df: pd.DataFrame,
    numeric_columns: list[str] | None = None,
    zscore_threshold: float = 3.0,
    iqr_factor: float = 1.5,
) -> tuple[pd.DataFrame, list[dict]]:
    if numeric_columns is None:
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()

    review_queue = []
    df_out = df.copy()
    df_out["_outlier_flags"] = ""

    for col in numeric_columns:
        values = df_out[col].dropna()
        if len(values) < 3:
            continue

        zscore_indices = _detect_zscore(values, zscore_threshold)
        iqr_indices = _detect_iqr(values, iqr_factor)

        all_outlier_idx = set(zscore_indices) | set(iqr_indices)
        for idx in all_outlier_idx:
            val = float(df_out.at[idx, col])
            z = _compute_zscore_single(values, val)
            entry = {
                "row_index": int(idx),
                "column": col,
                "value": val,
                "z_score": round(z, 3) if z is not None else None,
                "flagged_by": [],
                "action": "pending_review",
            }
            if idx in zscore_indices:
                entry["flagged_by"].append("zscore")
            if idx in iqr_indices:
                entry["flagged_by"].append("iqr")

            if "student_id" in df_out.columns:
                entry["student_id"] = str(df_out.at[idx, "student_id"])

            review_queue.append(entry)

            existing = df_out.at[idx, "_outlier_flags"]
            df_out.at[idx, "_outlier_flags"] = f"{existing},{col}" if existing else col

    logger.info("Outlier detection: %d outlier entries found across %d columns",
                len(review_queue), len(numeric_columns))
    return df_out, review_queue


def _detect_zscore(values: pd.Series, threshold: float) -> list[int]:
    mean = values.mean()
    std = values.std()
    if std == 0:
        return []
    z_scores = np.abs((values - mean) / std)
    return list(values.index[z_scores > threshold])


def _detect_iqr(values: pd.Series, factor: float) -> list[int]:
    q1 = values.quantile(0.25)
    q3 = values.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - factor * iqr
    upper = q3 + factor * iqr
    mask = (values < lower) | (values > upper)
    return list(values.index[mask])


def _compute_zscore_single(values: pd.Series, val: float):
    std = values.std()
    if std == 0:
        return None
    return abs((val - values.mean()) / std)
