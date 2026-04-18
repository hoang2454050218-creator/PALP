"""Shared analytics constants used by both tasks (writers) and health (readers)."""

CELERY_HEALTH_PING_CACHE_KEY = "palp:celery:health_ping"
CELERY_HEALTH_PING_TTL_SECONDS = 1800
CELERY_HEALTH_PING_STALE_THRESHOLD_SECONDS = 600
# All Celery queues we want to monitor for backlog. Keep in sync with
# ``CELERY_TASK_ROUTES`` in ``palp.settings.base`` so a new queue cannot be
# routed to without showing up in the deep-health endpoint and Prometheus
# gauge.
CELERY_DEFAULT_QUEUES = ("celery", "default", "events_high", "events_dlq")
