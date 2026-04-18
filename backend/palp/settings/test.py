import os

from .base import *  # noqa: F401, F403

DEBUG = False
SECRET_KEY = "test-secret-key-not-for-production"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("TEST_POSTGRES_DB", "palp"),
        "USER": os.environ.get("TEST_POSTGRES_USER", "palp"),
        "PASSWORD": os.environ.get("TEST_POSTGRES_PASSWORD", "palp_dev_password"),
        "HOST": os.environ.get("TEST_POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("TEST_POSTGRES_PORT", "5435"),
        "TEST": {
            "NAME": "palp_test",
        },
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

NPLUSONE_RAISE = True

# Disable DRF throttling in tests so rapid-fire suites don't hit rate limits.
# Specific throttle classes are still importable and individually unit-testable.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405 (defined in base.py via wildcard import)
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

# Brute-force protection off for tests -- individual axes tests use
# ``override_settings(AXES_ENABLED=True)`` to verify the lockout flow.
AXES_ENABLED = False
# Async event emission off for tests so unit tests stay synchronous.
PALP_ASYNC_EVENTS = False

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"], "level": "CRITICAL"},
}
