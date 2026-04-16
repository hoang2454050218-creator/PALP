import logging
import pandas as pd

logger = logging.getLogger("palp.etl")

REQUIRED_COLUMNS = {
    "student_id": "object",
    "course_code": "object",
    "semester": "object",
}

EXPECTED_SCHEMA = {
    "student_id": {"type": "object", "nullable": False},
    "course_code": {"type": "object", "nullable": False},
    "semester": {"type": "object", "nullable": False},
    "gpa": {"type": "float64", "nullable": True, "min": 0, "max": 10},
    "attendance_pct": {"type": "float64", "nullable": True, "min": 0, "max": 100},
    "total_credits": {"type": "float64", "nullable": True, "min": 0},
}


class SchemaValidationError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__(f"Schema validation failed: {len(errors)} error(s)")


def validate_schema(df: pd.DataFrame) -> dict:
    errors = []
    warnings = []

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            errors.append({"column": col, "error": "missing_required_column"})

    for col in df.columns:
        if col in EXPECTED_SCHEMA:
            spec = EXPECTED_SCHEMA[col]
            if not spec["nullable"] and df[col].isna().any():
                errors.append({
                    "column": col,
                    "error": "unexpected_nulls",
                    "null_count": int(df[col].isna().sum()),
                })

            if "min" in spec:
                below = df[col].dropna() < spec["min"]
                if below.any():
                    errors.append({
                        "column": col,
                        "error": "below_minimum",
                        "min": spec["min"],
                        "violating_count": int(below.sum()),
                    })

            if "max" in spec:
                above = df[col].dropna() > spec["max"]
                if above.any():
                    errors.append({
                        "column": col,
                        "error": "above_maximum",
                        "max": spec["max"],
                        "violating_count": int(above.sum()),
                    })

    for col in df.columns:
        if col not in EXPECTED_SCHEMA:
            warnings.append({"column": col, "warning": "unknown_column"})

    snapshot = {
        "columns": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "row_count": len(df),
        "null_counts": {col: int(df[col].isna().sum()) for col in df.columns},
    }

    if errors:
        raise SchemaValidationError(errors)

    return {"snapshot": snapshot, "warnings": warnings}


def detect_duplicate_keys(df: pd.DataFrame, key_columns: list[str]) -> pd.DataFrame:
    available_keys = [k for k in key_columns if k in df.columns]
    if not available_keys:
        return pd.DataFrame()

    duplicated_mask = df.duplicated(subset=available_keys, keep=False)
    return df[duplicated_mask]
