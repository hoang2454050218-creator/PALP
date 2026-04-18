import os

import sentry_sdk
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401, F403

DEBUG = False

if SECRET_KEY == "insecure-dev-key-change-me":  # noqa: F405
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set in production.")

if not os.environ.get("POSTGRES_PASSWORD"):
    raise ImproperlyConfigured("POSTGRES_PASSWORD must be set in production.")

if not os.environ.get("PII_ENCRYPTION_KEY"):
    raise ImproperlyConfigured("PII_ENCRYPTION_KEY must be set in production.")

_raw_hosts = os.environ.get("DJANGO_ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h.strip() for h in _raw_hosts.split(",") if h.strip()]
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must be set to a comma-separated list of valid hostnames in production."
    )

_raw_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "")
CORS_ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]
if not CORS_ALLOWED_ORIGINS:
    raise ImproperlyConfigured(
        "CORS_ALLOWED_ORIGINS must be set to a comma-separated list of allowed origins in production."
    )
CORS_ALLOW_CREDENTIALS = True

# TLS / HTTPS
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookie hardening
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
CSRF_COOKIE_SAMESITE = "Strict"
SESSION_COOKIE_NAME = "__Host-sessionid"

# Security headers
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"


# Sentry
def _scrub_pii_from_event(event, hint):
    if "request" in event:
        req = event["request"]
        if "data" in req:
            req["data"] = "[REDACTED]"
        if "cookies" in req:
            req["cookies"] = "[REDACTED]"
        headers = req.get("headers", {})
        for key in ("Authorization", "Cookie"):
            if key in headers:
                headers[key] = "[REDACTED]"

    user_ctx = event.get("user", {})
    for key in ("email", "username", "ip_address"):
        if key in user_ctx:
            user_ctx[key] = "[REDACTED]"

    return event


sentry_dsn = os.environ.get("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", 0.3)),
        profiles_sample_rate=float(os.environ.get("SENTRY_PROFILES_SAMPLE_RATE", 0.1)),
        send_default_pii=False,
        before_send=_scrub_pii_from_event,
        environment=os.environ.get("SENTRY_ENVIRONMENT", "production"),
        release=os.environ.get("APP_VERSION", "unknown"),
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
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s %(pathname)s %(lineno)d",
        },
        "audit_json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s AUDIT %(message)s",
        },
    },
    "handlers": {
        "console_json": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["request_id", "pii_scrub"],
        },
        "audit_console": {
            "class": "logging.StreamHandler",
            "formatter": "audit_json",
        },
    },
    "root": {
        "handlers": ["console_json"],
        "level": "WARNING",
    },
    "loggers": {
        "palp": {
            "handlers": ["console_json"],
            "level": "INFO",
            "propagate": False,
        },
        "palp.audit": {
            "handlers": ["audit_console"],
            "level": "INFO",
            "propagate": False,
        },
        "palp.performance": {
            "handlers": ["console_json"],
            "level": "WARNING",
            "propagate": False,
        },
        "palp.health": {
            "handlers": ["console_json"],
            "level": "INFO",
            "propagate": False,
        },
        "palp.celery": {
            "handlers": ["console_json"],
            "level": "INFO",
            "propagate": False,
        },
        "palp.privacy": {
            "handlers": ["console_json"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console_json"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
