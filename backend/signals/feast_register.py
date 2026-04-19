"""
Register the SignalSession / BehaviorScore feature views in MLOps.

Called from a Django ``ready`` hook so downstream models (RiskScore,
DKT, Bandit) can declare dependencies on these features by name without
manually reflecting the source tables.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("palp")


SIGNAL_SESSION_FEATURES = [
    {"name": "focus_minutes", "dtype": "float", "ttl_seconds": 600},
    {"name": "idle_minutes", "dtype": "float", "ttl_seconds": 600},
    {"name": "tab_switches", "dtype": "int", "ttl_seconds": 600},
    {"name": "hint_count", "dtype": "int", "ttl_seconds": 600},
    {"name": "frustration_score", "dtype": "float", "ttl_seconds": 600},
    {"name": "give_up_count", "dtype": "int", "ttl_seconds": 600},
    {"name": "session_quality", "dtype": "float", "ttl_seconds": 600},
]

BEHAVIOR_SCORE_FEATURES = [
    {"name": "total_focus_minutes", "dtype": "float", "ttl_seconds": 86400},
    {"name": "avg_focus_score", "dtype": "float", "ttl_seconds": 86400},
    {"name": "avg_frustration_score", "dtype": "float", "ttl_seconds": 86400},
    {"name": "total_give_up_count", "dtype": "int", "ttl_seconds": 86400},
    {"name": "total_struggle_count", "dtype": "int", "ttl_seconds": 86400},
    {"name": "sessions_count", "dtype": "int", "ttl_seconds": 86400},
]


def register_signal_feature_views() -> None:
    """Idempotent registration. Safe to call multiple times."""
    try:
        from mlops.feature_store import register_view
    except ImportError:
        logger.debug("mlops app not available; skipping feature view registration")
        return

    try:
        register_view(
            name="student.signal_session",
            entity="student",
            source_table="palp_signal_session",
            features=SIGNAL_SESSION_FEATURES,
            online_store_enabled=True,
            description=(
                "5-minute behavioural rollup per student. Source for "
                "RiskScore behavioral dimension, FSRS cognitive load, "
                "and bandit context."
            ),
        )
        register_view(
            name="student.behavior_score_daily",
            entity="student",
            source_table="palp_behavior_score",
            features=BEHAVIOR_SCORE_FEATURES,
            online_store_enabled=False,
            description=(
                "Daily rollup of SignalSession. Used for trend charts "
                "and survival-model time-varying covariates."
            ),
        )
    except Exception:
        logger.exception("Failed to register signal feature views (non-fatal)")
