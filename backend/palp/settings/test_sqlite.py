"""Local-only test settings using SQLite.

Used as a fallback when the Docker Postgres container is unavailable on
the developer's machine. Mirrors ``test.py`` in every other respect so
that the same test code runs unchanged.

DO NOT use this in CI or production. Some Postgres-specific behaviour
(JSONB queries, advisory locks, full-text search) is approximated only,
so a small number of tests that rely on those features may behave
differently. The full Postgres-based ``test.py`` settings remain the
source of truth.
"""

from .test import *  # noqa: F401, F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
