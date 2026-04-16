import os

from .base import *  # noqa: F401, F403

DEBUG = False
SECRET_KEY = "test-secret-key-not-for-production"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("TEST_POSTGRES_DB", "palp_test"),
        "USER": os.environ.get("TEST_POSTGRES_USER", "palp"),
        "PASSWORD": os.environ.get("TEST_POSTGRES_PASSWORD", "palp_dev_password"),
        "HOST": os.environ.get("TEST_POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("TEST_POSTGRES_PORT", "5432"),
        "TEST": {
            "NAME": os.environ.get("TEST_POSTGRES_DB", "palp_test"),
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

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"], "level": "CRITICAL"},
}
