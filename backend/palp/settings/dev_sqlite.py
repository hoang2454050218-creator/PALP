"""Bare-metal dev settings for browser/manual testing without Docker.

Use this when Docker Desktop is unavailable on the developer's machine
but you still need a working backend to demo or browser-test the UI.

DO NOT use this in production or CI. It uses SQLite, in-memory cache,
and synchronous Celery -- which is great for a quick smoke test on the
host machine but lacks Postgres-only features used elsewhere.
"""

import os
from pathlib import Path


def _load_dotenv_into_environ() -> None:
    """Tiny zero-dep ``.env`` loader.

    The bare-metal dev workflow doesn't run under Docker Compose, so
    nothing is shoving env vars into the process for us. We do a
    one-shot read of the project-root ``.env`` here so any value the
    operator drops into the file shows up in ``os.environ`` *before*
    ``base.py`` materialises the ``PALP_COACH`` block. Idempotent — if
    a var already exists in the real environment we leave it alone
    (real env wins, file is the fallback).
    """
    root = Path(__file__).resolve().parent.parent.parent.parent
    env_file = root / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv_into_environ()

from .base import *  # noqa: E402, F401, F403

DEBUG = True
SECRET_KEY = "dev-only-not-for-production-do-not-deploy"
ALLOWED_HOSTS = ["*"]

_DB_PATH = Path(__file__).resolve().parent.parent.parent / "dev_sqlite.sqlite3"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(_DB_PATH),
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Disable the auxiliary Prometheus exporter that ``django_prometheus`` opens
# on the first port in PROMETHEUS_METRICS_EXPORT_PORT_RANGE. In production
# that runs on a side port reachable only from Nginx; in this bare-metal
# dev mode we don't need it and it would otherwise compete with whatever
# port Django runserver is bound to.
PROMETHEUS_METRICS_EXPORT_PORT_RANGE = []

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

PALP_ASYNC_EVENTS = False
NPLUSONE_RAISE = False
AXES_ENABLED = False

CORS_ALLOW_ALL_ORIGINS = True
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3002",
    "http://127.0.0.1:3002",
]

REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {
        "anon": None,
        "user": None,
        "login": None,
        "register": None,
        "assessment_submit": None,
        "export": None,
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
}
