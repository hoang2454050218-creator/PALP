import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

_default_key = "insecure-dev-key-change-me"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", _default_key)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "django_celery_beat",
    "drf_spectacular",
    "django_prometheus",
    "axes",
    # Local apps
    "accounts",
    "assessment",
    "adaptive",
    "curriculum",
    "dashboard",
    "analytics",
    "events",
    "wellbeing",
    "privacy",
    "featureflags",
    "experiments",
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "palp.middleware.RequestIDMiddleware",
    "palp.middleware.RequestIDLoggingMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "accounts.middleware.AuthAuditMiddleware",
    "palp.middleware.RequestTimingMiddleware",
    "palp.middleware.RequestMetricsMiddleware",
    "palp.metrics_middleware.PrometheusMetricsMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "privacy.middleware.ConsentGateMiddleware",
    "privacy.middleware.AuditMiddleware",
    # Axes must be the LAST middleware so it sees authentication results.
    "axes.middleware.AxesMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

AUTHENTICATION_BACKENDS = [
    # Axes must be FIRST so it can short-circuit locked-out attempts.
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

ROOT_URLCONF = "palp.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "palp.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django_prometheus.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "palp"),
        "USER": os.environ.get("POSTGRES_USER", "palp"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "palp_dev_password"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", 600)),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "connect_timeout": 5,
            "options": "-c statement_timeout=30000",
        },
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_prometheus.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "vi"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# DRF
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("accounts.authentication.CookieJWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "30/minute",
        "user": "120/minute",
        "login": "10/minute",
        "register": "5/minute",
        "assessment_submit": "30/minute",
        "export": "5/minute",
    },
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "palp.exception_handler.palp_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.environ.get("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", 60))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.environ.get("JWT_REFRESH_TOKEN_LIFETIME_DAYS", 7))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "PALP API",
    "DESCRIPTION": "Personalized Adaptive Learning Platform API",
    "VERSION": "1.0.0",
    # Allow `manage.py spectacular` to emit a baseline file despite incomplete @extend_schema coverage.
    # CI sets OPENAPI_RELAXED=1; keep False locally to surface schema issues during development.
    "DISABLE_ERRORS_AND_WARNINGS": os.environ.get("OPENAPI_RELAXED", "").lower() in ("1", "true", "yes"),
}

# Celery
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND",
    os.environ.get("REDIS_URL", "redis://localhost:6379/2"),
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300
CELERY_TASK_SOFT_TIME_LIMIT = 240
CELERY_WORKER_MAX_TASKS_PER_CHILD = 500

# Per-task routing -- hot-path event emission goes to a high-priority queue
# with retries + DLQ so SubmitTaskAttempt etc. don't block on event writes.
CELERY_TASK_ROUTES = {
    "events.tasks.emit_event_task": {"queue": "events_high"},
    "events.tasks.dead_letter_event": {"queue": "events_dlq"},
}
CELERY_TASK_QUEUES_DEFAULT = ("celery", "default", "events_high", "events_dlq")

# Toggle async event emission. OFF by default for local dev / tests so the
# stack stays predictable; production compose flips it ON.
PALP_ASYNC_EVENTS = os.environ.get("PALP_ASYNC_EVENTS", "false").lower() in (
    "true", "1", "yes",
)

from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    "nightly-early-warnings": {
        "task": "analytics.tasks.run_nightly_early_warnings",
        "schedule": crontab(hour=2, minute=0),
    },
    "weekly-report": {
        "task": "analytics.tasks.generate_weekly_report",
        "schedule": crontab(hour=6, minute=0, day_of_week="sunday"),
    },
    "celery-health-ping": {
        "task": "analytics.tasks.celery_health_ping",
        "schedule": crontab(minute="*/5"),
    },
    "queue-backlog-check": {
        "task": "analytics.tasks.check_queue_backlog",
        "schedule": crontab(minute="*/3"),
    },
    "backup-age-metric": {
        "task": "analytics.tasks.update_backup_age_metric",
        "schedule": crontab(minute="*/15"),
    },
    "weekly-restore-drill": {
        "task": "analytics.tasks.weekly_restore_drill",
        "schedule": crontab(hour=3, minute=0, day_of_week="sunday"),
    },
    "privacy-retention-enforcement": {
        "task": "privacy.enforce_retention",
        "schedule": crontab(hour=3, minute=0),
    },
    "privacy-incident-sla-check": {
        "task": "privacy.check_incident_sla",
        "schedule": crontab(minute="*/60"),
    },
}

# PALP-specific config
PALP_BKT_DEFAULTS = {
    "P_L0": 0.3,
    "P_TRANSIT": 0.09,
    "P_GUESS": 0.25,
    "P_SLIP": 0.10,
}

PALP_ADAPTIVE_THRESHOLDS = {
    "MASTERY_LOW": 0.60,
    "MASTERY_HIGH": 0.85,
    "MIN_ATTEMPTS_FOR_ADVANCE": 3,
}

PALP_WELLBEING = {
    "CONTINUOUS_STUDY_LIMIT_MINUTES": 50,
}

PALP_EARLY_WARNING = {
    "INACTIVITY_YELLOW_DAYS": 3,
    "INACTIVITY_RED_DAYS": 5,
    "RETRY_FAILURE_THRESHOLD": 3,
}

PALP_SLO = {
    "PAGE_LOAD_P95_MS": 2000,
    "ADAPTIVE_DECISION_P95_MS": 1500,
    "DASHBOARD_LOAD_P95_MS": 2000,
    "PROGRESS_UPDATE_P95_MS": 500,
    "ERROR_RATE_PERCENT": 0.5,
    "CONCURRENT_USERS_STABLE": 200,
    "CONCURRENT_USERS_SPIKE": 300,
    "UPTIME_CLASS_HOURS_PERCENT": 99.9,
}

PALP_QUEUE_ALERT = {
    "WARN": int(os.environ.get("QUEUE_ALERT_WARN", 50)),
    "CRITICAL": int(os.environ.get("QUEUE_ALERT_CRITICAL", 200)),
}

# Observability
PALP_EVENT_COMPLETENESS_THRESHOLD = 0.995
PALP_EVENT_DUPLICATION_THRESHOLD = 0.001
PALP_EVENTS_REQUIRING_CONFIRMATION = [
    "assessment_completed",
    "micro_task_completed",
    "gv_action_taken",
]

PROMETHEUS_METRICS_EXPORT_PORT_RANGE = range(8001, 8050)
PROMETHEUS_METRICS_EXPORT_ADDRESS = ""

# Networks allowed to scrape /metrics. Override via env in production if the
# scraper sits outside the standard private ranges (e.g. dedicated monitoring VPC).
_metrics_networks_raw = os.environ.get("PALP_METRICS_ALLOWED_NETWORKS", "")
if _metrics_networks_raw:
    PALP_METRICS_ALLOWED_NETWORKS = tuple(
        n.strip() for n in _metrics_networks_raw.split(",") if n.strip()
    )
else:
    PALP_METRICS_ALLOWED_NETWORKS = (
        "127.0.0.0/8",
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "::1/128",
        "fc00::/7",
    )

# Celery monitored queues (used by check_queue_backlog + deep health view).
# Sourced from analytics.constants so the canonical list lives in one place.
from analytics.constants import CELERY_DEFAULT_QUEUES as _CELERY_DEFAULT_QUEUES  # noqa: E402

PALP_CELERY_MONITORED_QUEUES = _CELERY_DEFAULT_QUEUES

# Backup volume mount path (shared between backup container and Django).
PALP_BACKUP_DIR = os.environ.get("PALP_BACKUP_DIR", "/backups")

# Restore drill freshness threshold for release gate (default 14 days).
PALP_RESTORE_DRILL_MAX_AGE_DAYS = int(
    os.environ.get("PALP_RESTORE_DRILL_MAX_AGE_DAYS", 14)
)
PALP_BACKUP_MAX_AGE_HOURS = int(
    os.environ.get("PALP_BACKUP_MAX_AGE_HOURS", 26)
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {
            "()": "palp.middleware.RequestIDLogFilter",
        },
        "pii_scrub": {
            "()": "privacy.middleware.PIIScrubLogFilter",
        },
    },
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} [rid:{request_id}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "filters": ["request_id", "pii_scrub"],
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "palp": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "palp.events": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "palp.performance": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "palp.health": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "palp.celery": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "palp.privacy": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Privacy
PALP_PRIVACY = {
    "SLA_HOURS": 48,
    "CONSENT_VERSION": "1.0",
}

# Security: PII encryption key (Fernet-compatible, 32-byte base64-encoded)
PII_ENCRYPTION_KEY = os.environ.get("PII_ENCRYPTION_KEY", "")

# django-axes brute-force protection
AXES_FAILURE_LIMIT = int(os.environ.get("AXES_FAILURE_LIMIT", 10))
AXES_COOLOFF_TIME = timedelta(
    minutes=int(os.environ.get("AXES_COOLOFF_MINUTES", 30))
)
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
# Default DB handler -- swap to AxesCacheHandler in production after we
# enable a Redis cache namespace dedicated to axes (Sprint 5 Vault work).
AXES_HANDLER = "axes.handlers.database.AxesDatabaseHandler"
AXES_VERBOSE = False
AXES_RESET_COOL_OFF_ON_FAILURE_DURING_LOCKOUT = False
# hCaptcha kicks in earlier than the lockout to provide a self-serve recovery
# instead of forcing the user to wait the full cool-off.
AXES_CAPTCHA_TRIGGER_FAILURES = int(
    os.environ.get("AXES_CAPTCHA_TRIGGER_FAILURES", 3)
)

# hCaptcha (https://www.hcaptcha.com/). Test keys are safe in dev: any answer
# verifies. Override with real keys via env in production.
HCAPTCHA_SITE_KEY = os.environ.get(
    "HCAPTCHA_SITE_KEY", "10000000-ffff-ffff-ffff-000000000001"
)
HCAPTCHA_SECRET_KEY = os.environ.get(
    "HCAPTCHA_SECRET_KEY", "0x0000000000000000000000000000000000000000"
)

# Audit log: paths that trigger logging
AUDIT_SENSITIVE_PREFIXES = [
    "/api/auth/profile/",
    "/api/dashboard/",
    "/api/analytics/",
    "/api/assessment/profile/",
    "/api/adaptive/student/",
    "/api/events/student/",
    "/api/auth/classes/",
    "/api/auth/export/",
]
