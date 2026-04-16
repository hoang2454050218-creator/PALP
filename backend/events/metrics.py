"""
Prometheus metrics for PALP observability.

Metrics are registered lazily so this module can be imported anywhere
without requiring django-prometheus at import time.
"""
from prometheus_client import Counter, Gauge, Histogram

HTTP_REQUESTS_TOTAL = Counter(
    "palp_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "palp_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

EVENT_INGESTION_TOTAL = Counter(
    "palp_event_ingestion_total",
    "Event ingestion count",
    ["event_name", "status"],
)

EVENT_COMPLETENESS = Gauge(
    "palp_event_completeness_ratio",
    "Ratio of events with all required fields populated",
)

EVENT_DUPLICATION = Gauge(
    "palp_event_duplication_ratio",
    "Estimated event duplication ratio",
)

ADAPTIVE_DECISION_DURATION = Histogram(
    "palp_adaptive_decision_duration_seconds",
    "Time to compute adaptive pathway decision",
    ["decision_type"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

CELERY_TASK_TOTAL = Counter(
    "palp_celery_task_total",
    "Celery task execution count",
    ["task_name", "status"],
)

ALERT_GENERATION_TOTAL = Counter(
    "palp_alert_generation_total",
    "Alert generation count",
    ["alert_type"],
)

DATA_QUALITY_SCORE = Gauge(
    "palp_data_quality_score",
    "Latest data quality score from ETL checks",
    ["source"],
)

BACKUP_AGE_SECONDS = Gauge(
    "palp_backup_age_seconds",
    "Seconds since last successful backup",
)

EXPORT_DELETE_REQUESTS = Counter(
    "palp_export_delete_requests_total",
    "GDPR data export/delete requests",
    ["request_type"],
)
