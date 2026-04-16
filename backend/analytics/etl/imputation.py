import logging
import numpy as np
import pandas as pd
from sklearn.impute import KNNImputer

logger = logging.getLogger("palp.etl")

HIGH_MISSING_THRESHOLD = 0.50


def classify_missing_mechanism(series: pd.Series) -> str:
    missing_pct = series.isna().sum() / len(series) if len(series) > 0 else 0
    if missing_pct == 0:
        return "complete"
    if missing_pct < 0.05:
        return "negligible"
    if missing_pct < 0.20:
        return "MAR_likely"
    if missing_pct < HIGH_MISSING_THRESHOLD:
        return "MAR_suspected"
    return "MNAR_suspected"


def impute_missing_values(
    df: pd.DataFrame,
    numeric_columns: list[str] | None = None,
    n_neighbors: int = 5,
) -> tuple[pd.DataFrame, dict]:
    report = {
        "columns_imputed": [],
        "columns_excluded": [],
        "column_details": {},
        "total_values_imputed": 0,
    }

    if numeric_columns is None:
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()

    cols_to_impute = []
    for col in numeric_columns:
        missing_pct = df[col].isna().sum() / len(df) if len(df) > 0 else 0
        mechanism = classify_missing_mechanism(df[col])

        report["column_details"][col] = {
            "missing_pct": round(missing_pct, 4),
            "mechanism": mechanism,
            "missing_count": int(df[col].isna().sum()),
        }

        if missing_pct >= HIGH_MISSING_THRESHOLD:
            report["columns_excluded"].append(col)
            report["column_details"][col]["action"] = "excluded"
            logger.warning(
                "Column '%s' excluded: %.1f%% missing (>50%% threshold)",
                col, missing_pct * 100,
            )
        elif missing_pct > 0:
            cols_to_impute.append(col)
        else:
            report["column_details"][col]["action"] = "complete"

    if not cols_to_impute:
        return df, report

    imputer = KNNImputer(n_neighbors=n_neighbors)
    original_nulls = df[cols_to_impute].isna().sum().sum()

    df_imputed = df.copy()
    df_imputed[cols_to_impute] = imputer.fit_transform(df[cols_to_impute])

    remaining_nulls = df_imputed[cols_to_impute].isna().sum().sum()
    total_imputed = int(original_nulls - remaining_nulls)

    report["columns_imputed"] = cols_to_impute
    report["total_values_imputed"] = total_imputed

    for col in cols_to_impute:
        imputed_count = int(df[col].isna().sum() - df_imputed[col].isna().sum())
        report["column_details"][col]["action"] = "knn_imputed"
        report["column_details"][col]["values_imputed"] = imputed_count

    return df_imputed, report
