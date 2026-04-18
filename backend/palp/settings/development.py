from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Specific origins instead of the wildcard so the browser allows
# `credentials: 'include'` (cookie-based JWT auth) -- the wildcard is
# rejected by Chrome/Firefox when credentials are present.
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:3003",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3002",
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False

# django-prometheus' thread-based exporter clashes with the dev autoreloader.
# In development we expose metrics solely via the URL endpoint mounted in
# palp/urls.py (/metrics), so the standalone port range is disabled.
PROMETHEUS_METRICS_EXPORT_PORT_RANGE = []

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "palp": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
