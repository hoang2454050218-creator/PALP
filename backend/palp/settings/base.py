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
    # Phase 0 — Foundation Science (v3 roadmap)
    "mlops",
    "fairness",
    "causal",
    "device_sessions",
    # Phase 1 — Sensing + RiskScore + Metacognitive (v3 roadmap)
    "signals",
    "risk",
    # Phase 2 — Direction Engine + SRL (v3 roadmap)
    "goals",
    # Phase 3 — Peer Engine, anti-herd, reciprocal teaching (v3 roadmap)
    "peer",
    # Phase 4 — Hybrid AI Coach + Emergency Pipeline + Notifications (v3 roadmap)
    "coach",
    "emergency",
    "notifications",
    # Phase 5 — Intelligence Upgrade: DKT + KG + Bandit + Agentic Memory (v3 roadmap)
    "dkt",
    "knowledge_graph",
    "bandit",
    "coach_memory",
    # Phase 6 — XAI + FSRS + Differential Privacy + Instructor Co-pilot (v3 roadmap)
    "explainability",
    "spacedrep",
    "privacy_dp",
    "instructor_copilot",
    # Phase 7 — Academic layer: Benchmarks + IRB + Publication + Affect (v3 roadmap)
    "benchmarks",
    "research",
    "publication",
    "affect",
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
    # v3 roadmap — Phase 2 Direction Engine
    "goals-detect-drift-periodic": {
        "task": "goals.detect_drift_periodic",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    "goals-open-weekly-reflections": {
        "task": "goals.open_weekly_reflections",
        # Saturday 18:00 Asia/Ho_Chi_Minh
        "schedule": crontab(hour=18, minute=0, day_of_week="saturday"),
    },
    # v3 roadmap — Phase 3 (Peer Engine)
    "peer-weekly-recompute-cohorts": {
        "task": "peer.weekly_recompute_cohorts",
        # Sunday 03:00 ICT — recompute ability cohorts weekly
        "schedule": crontab(hour=3, minute=0, day_of_week="sunday"),
    },
    "peer-daily-detect-herds": {
        "task": "peer.daily_detect_herds",
        # 04:00 ICT daily after the early-warning batch settles
        "schedule": crontab(hour=4, minute=0),
    },
    "peer-prompt-optin-after-4w": {
        "task": "peer.prompt_optin_after_4w",
        # Mondays 09:00 ICT — surface 4-week opt-in prompts
        "schedule": crontab(hour=9, minute=0, day_of_week="monday"),
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

# v3 roadmap — Phase 0 Foundation Science
PALP_FAIRNESS = {
    "DISPARATE_IMPACT_THRESHOLD": float(os.environ.get("PALP_FAIRNESS_DI", 0.8)),
    "EQUALIZED_ODDS_TOLERANCE": float(os.environ.get("PALP_FAIRNESS_EOD", 0.1)),
    "CALIBRATION_TOLERANCE": float(os.environ.get("PALP_FAIRNESS_CAL", 0.05)),
    "CLUSTER_CONCENTRATION_MAX": float(os.environ.get("PALP_FAIRNESS_CLUSTER_MAX", 0.7)),
    "CLUSTER_MIN_BASELINE": float(os.environ.get("PALP_FAIRNESS_CLUSTER_MIN_BASE", 0.5)),
}
PALP_CAUSAL = {
    "MIN_SAMPLE_SIZE": int(os.environ.get("PALP_CAUSAL_MIN_N", 100)),
    "DEFAULT_ALPHA": float(os.environ.get("PALP_CAUSAL_ALPHA", 0.05)),
    "DEFAULT_POWER": float(os.environ.get("PALP_CAUSAL_POWER", 0.80)),
    "CUPED_ENABLED": os.environ.get("PALP_CAUSAL_CUPED", "true").lower() in ("true", "1", "yes"),
}
PALP_MLOPS = {
    "FEATURE_STORE_TTL_SECONDS": int(os.environ.get("PALP_MLOPS_FS_TTL", 300)),
    "MLFLOW_TRACKING_URI": os.environ.get("MLFLOW_TRACKING_URI", ""),
    "DRIFT_MIN_SAMPLE": int(os.environ.get("PALP_MLOPS_DRIFT_MIN_N", 50)),
}
PALP_DEVICE_SESSIONS = {
    "LINK_PROXIMITY_SECONDS": int(os.environ.get("PALP_DEVSESS_PROXIMITY_S", 300)),
    "FINGERPRINT_RETENTION_DAYS": int(os.environ.get("PALP_DEVSESS_RETENTION_D", 30)),
}
PALP_DP = {
    "EPSILON_BUDGET_PER_RUN": float(os.environ.get("PALP_DP_EPSILON_PER_RUN", 1.0)),
    "EPSILON_BUDGET_PER_STUDENT_YEAR": float(os.environ.get("PALP_DP_EPSILON_PER_YEAR", 5.0)),
    "DELTA": float(os.environ.get("PALP_DP_DELTA", 1e-5)),
    "NOISE_MULTIPLIER": float(os.environ.get("PALP_DP_NOISE_MULT", 1.1)),
    "MAX_GRAD_NORM": float(os.environ.get("PALP_DP_MAX_GRAD_NORM", 1.0)),
    "COHORT_MIN_SIZE_FOR_DP": int(os.environ.get("PALP_DP_COHORT_MIN", 10)),
}
PALP_FINOPS = {
    "MONTHLY_COST_BUDGET_USD": int(os.environ.get("PALP_FINOPS_BUDGET_USD", 5000)),
    "DAILY_TOKEN_LIMIT_PER_USER": int(os.environ.get("PALP_FINOPS_DAILY_TOKENS_USER", 50_000)),
    "DAILY_TOKEN_ALERT_PER_CLASS": int(os.environ.get("PALP_FINOPS_DAILY_TOKENS_CLASS", 500_000)),
}

# v3 roadmap — Phase 1F RiskScore weights. CI test asserts these sum to
# 1.0; per-component contribution is bounded by the dimension weight so a
# single noisy signal can never drive the composite above its dimension's
# share.
PALP_RISK_WEIGHTS = {
    "academic": float(os.environ.get("PALP_RISK_W_ACADEMIC", 0.30)),
    "behavioral": float(os.environ.get("PALP_RISK_W_BEHAVIORAL", 0.25)),
    "engagement": float(os.environ.get("PALP_RISK_W_ENGAGEMENT", 0.20)),
    "psychological": float(os.environ.get("PALP_RISK_W_PSYCH", 0.10)),
    "metacognitive": float(os.environ.get("PALP_RISK_W_METACOG", 0.15)),
}
PALP_RISK_THRESHOLDS = {
    "ALERT_YELLOW": float(os.environ.get("PALP_RISK_ALERT_YELLOW", 60.0)),
    "ALERT_RED": float(os.environ.get("PALP_RISK_ALERT_RED", 80.0)),
    "INACTIVITY_DAYS_HARD_RED": int(os.environ.get("PALP_RISK_INACTIVITY_HARD_RED", 14)),
}

# v3 roadmap — Phase 2 Direction Engine
PALP_GOALS = {
    "DRIFT_THRESHOLD_PCT": float(os.environ.get("PALP_GOALS_DRIFT_PCT", 0.40)),
    "DAILY_PLAN_MAX_ITEMS": int(os.environ.get("PALP_GOALS_DAILY_MAX", 3)),
    "REFLECTION_OPEN_HOUR_LOCAL": int(os.environ.get("PALP_GOALS_REFLECTION_HOUR", 18)),
    "REFLECTION_OPEN_DOW": os.environ.get("PALP_GOALS_REFLECTION_DOW", "saturday"),
}

# Phase 4 — Hybrid AI Coach + Emergency Pipeline + Notifications (v3 roadmap).
# Tunable via env so a release can flip provider or thresholds without
# code changes. The defaults match the safety playbook ("never trust the
# vendor; always run the safety pipeline locally first").
PALP_COACH = {
    # LLM routing & providers
    # ``DEFAULT_PROVIDER`` is the safety net — used when neither cloud nor
    # local is reachable. We keep it as ``echo`` so a fresh dev install
    # works without any key. Operators upgrade by setting the two block
    # keys below + flipping CLOUD_PROVIDER to ``openai_compat``.
    "DEFAULT_PROVIDER": os.environ.get("PALP_COACH_DEFAULT_PROVIDER", "echo"),
    "CLOUD_PROVIDER": os.environ.get("PALP_COACH_CLOUD_PROVIDER", "echo"),
    "LOCAL_PROVIDER": os.environ.get("PALP_COACH_LOCAL_PROVIDER", "echo"),
    # OpenAI-compatible cloud client (works with OpenAI direct, key4u.shop,
    # OpenRouter, Azure shim, vLLM, etc.). Picked up by
    # ``coach.llm.client._make_openai_compat`` when CLOUD_PROVIDER is
    # set to ``openai_compat``.
    "OPENAI_COMPAT": {
        "API_KEY": os.environ.get("OPENAI_COMPAT_API_KEY", ""),
        "BASE_URL": os.environ.get(
            "OPENAI_COMPAT_BASE_URL", "https://api.openai.com/v1",
        ),
        "MODEL": os.environ.get("OPENAI_COMPAT_MODEL", "gpt-4o-mini"),
        "PROVIDER_LABEL": os.environ.get(
            "OPENAI_COMPAT_PROVIDER_LABEL", "openai_compat",
        ),
        "TIMEOUT_SECONDS": float(
            os.environ.get("OPENAI_COMPAT_TIMEOUT_SECONDS", 30.0)
        ),
        "MAX_OUTPUT_TOKENS": int(
            os.environ.get("OPENAI_COMPAT_MAX_OUTPUT_TOKENS", 1024)
        ),
        "TEMPERATURE": float(os.environ.get("OPENAI_COMPAT_TEMPERATURE", 0.4)),
    },
    # Local Ollama daemon for PII-sensitive intents.
    "OLLAMA": {
        "BASE_URL": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        "MODEL": os.environ.get("OLLAMA_MODEL", "qwen2.5:7b"),
        "TIMEOUT_SECONDS": float(os.environ.get("OLLAMA_TIMEOUT_SECONDS", 60.0)),
        "TEMPERATURE": float(os.environ.get("OLLAMA_TEMPERATURE", 0.4)),
        "NUM_PREDICT": int(os.environ.get("OLLAMA_NUM_PREDICT", 1024)),
    },
    # Cost & rate-limit
    "DAILY_TOKEN_LIMIT_PER_USER": int(
        os.environ.get("PALP_COACH_DAILY_TOKEN_LIMIT", 50_000)
    ),
    "DAILY_TOKEN_ALERT_PER_CLASS": int(
        os.environ.get("PALP_COACH_DAILY_CLASS_ALERT", 1_000_000)
    ),
    "MAX_TURNS_PER_CONVERSATION": int(
        os.environ.get("PALP_COACH_MAX_TURNS_PER_CONV", 40)
    ),
    "MAX_INPUT_LENGTH": int(os.environ.get("PALP_COACH_MAX_INPUT_LEN", 4000)),
    # Safety
    "JAILBREAK_THRESHOLD": float(os.environ.get("PALP_COACH_JAILBREAK_THRESHOLD", 0.7)),
    "JAILBREAK_COOLDOWN_HOURS": int(
        os.environ.get("PALP_COACH_JAILBREAK_COOLDOWN_HOURS", 24)
    ),
    "JAILBREAK_ATTEMPTS_BEFORE_COOLDOWN": int(
        os.environ.get("PALP_COACH_JAILBREAK_ATTEMPTS", 3)
    ),
}

PALP_EMERGENCY = {
    "SLA_MINUTES": int(os.environ.get("PALP_EMERGENCY_SLA_MINUTES", 15)),
    "FOLLOW_UP_HOURS": [24, 48, 72],
}

# Phase 5 — Intelligence upgrade tuning blocks (v3 roadmap).
PALP_DKT = {
    "EMBED_DIM": int(os.environ.get("PALP_DKT_EMBED_DIM", 16)),
    "MAX_HISTORY": int(os.environ.get("PALP_DKT_MAX_HISTORY", 64)),
    "TEMPERATURE": float(os.environ.get("PALP_DKT_TEMPERATURE", 1.0)),
    "SEED": int(os.environ.get("PALP_DKT_SEED", 42)),
    "TOP_K_DEFAULT": int(os.environ.get("PALP_DKT_TOP_K", 10)),
}
PALP_KG = {
    "MAX_DEPTH": int(os.environ.get("PALP_KG_MAX_DEPTH", 4)),
    "DEFAULT_EDGE_STRENGTH": float(os.environ.get("PALP_KG_DEFAULT_STRENGTH", 0.7)),
}
PALP_BANDIT = {
    "DEFAULT_REWARD_WINDOW_MIN": int(
        os.environ.get("PALP_BANDIT_REWARD_WINDOW_MIN", 24 * 60)
    ),
    "DEFAULT_SEED": int(os.environ.get("PALP_BANDIT_SEED", 42)),
}
PALP_MEMORY = {
    "MAX_RECALL_EPISODIC": int(os.environ.get("PALP_MEMORY_MAX_EPISODIC", 5)),
    "MAX_RECALL_SEMANTIC": int(os.environ.get("PALP_MEMORY_MAX_SEMANTIC", 5)),
    "MAX_RECALL_PROCEDURAL": int(os.environ.get("PALP_MEMORY_MAX_PROCEDURAL", 3)),
}

# Phase 6 — XAI + FSRS + DP + Co-pilot tuning blocks (v3 roadmap).
PALP_XAI = {
    "TARGET_DELTA": float(os.environ.get("PALP_XAI_TARGET_DELTA", 10.0)),
    "MAX_COUNTERFACTUALS": int(os.environ.get("PALP_XAI_MAX_CF", 5)),
}
PALP_SPACEDREP = {
    "TARGET_RETENTION": float(os.environ.get("PALP_FSRS_TARGET_RETENTION", 0.9)),
    # 17 default FSRS-4.5 weights from the open-source community.
    # Override only when a fitter has produced per-deployment values.
    "WEIGHTS": None,
    "DEFAULT_NEW_PER_DAY": int(os.environ.get("PALP_FSRS_NEW_PER_DAY", 5)),
}
PALP_DP = {
    "DEFAULT_SCOPE": os.environ.get("PALP_DP_DEFAULT_SCOPE", "global:weekly"),
    "DEFAULT_PERIOD_DAYS": int(os.environ.get("PALP_DP_PERIOD_DAYS", 7)),
    "DEFAULT_EPSILON_TOTAL": float(
        os.environ.get("PALP_DP_DEFAULT_EPSILON", 1.0)
    ),
}
PALP_COPILOT = {
    "MAX_DRAFTS_PER_DAY": int(os.environ.get("PALP_COPILOT_MAX_DRAFTS", 50)),
}

# Phase 7 — Academic layer tuning blocks (v3 roadmap).
PALP_BENCHMARKS = {
    "DEFAULT_SAMPLE_SIZE": int(os.environ.get("PALP_BENCH_SAMPLE", 200)),
    "DEFAULT_SEED": int(os.environ.get("PALP_BENCH_SEED", 42)),
    # Loaders are dotted import paths -> callables. We default to the
    # built-in synthetic loaders so the test suite + offline dev never
    # breaks. Operators override via env to point at the real datasets.
    "LOADERS": {
        "ednet": os.environ.get(
            "PALP_BENCH_LOADER_EDNET",
            "benchmarks.loaders.ednet_synthetic",
        ),
        "assistments_2009": os.environ.get(
            "PALP_BENCH_LOADER_AS2009",
            "benchmarks.loaders.assistments_2009_synthetic",
        ),
    },
}
PALP_RESEARCH = {
    "K_ANONYMITY_K": int(os.environ.get("PALP_RESEARCH_K", 5)),
    "DEFAULT_PROTOCOL_RETENTION_MONTHS": int(
        os.environ.get("PALP_RESEARCH_RETENTION", 12)
    ),
    # Salt for hashing student ids in anonymized exports. Operators MUST
    # rotate this in production; the dev default is intentionally
    # non-secret so the test suite is reproducible.
    "ID_HASH_SALT": os.environ.get(
        "PALP_RESEARCH_HASH_SALT", "palp-research-dev-salt"
    ),
    "SUPPRESS_QUASI_IDENTIFIERS": [
        "first_name", "last_name", "email", "phone", "student_id",
    ],
}
PALP_PUBLICATION = {
    "AUTHORS_DEFAULT": [
        {"name": "PALP Team", "role": "Engineering"},
    ],
    "LICENCE_DEFAULT": "CC-BY-4.0",
}
PALP_AFFECT = {
    "MIN_SAMPLE_KEYSTROKES": int(os.environ.get("PALP_AFFECT_MIN_KS", 10)),
    "MIN_SAMPLE_TEXT_LEN": int(os.environ.get("PALP_AFFECT_MIN_TEXT", 8)),
    "DEFAULT_LANG": os.environ.get("PALP_AFFECT_DEFAULT_LANG", "vi"),
}

# Phase 3 — Peer Engine, anti-herd, reciprocal teaching (v3 roadmap).
# Tuning lives here so a release can change thresholds without code
# changes. The defaults match the design document and are intentionally
# conservative — anti-herd thresholds err on the side of caution
# because false positives lecturer-side are recoverable, false negatives
# are not.
PALP_PEER = {
    # Cohort
    "COHORT_TARGET_SIZE": int(os.environ.get("PALP_PEER_COHORT_TARGET", 25)),
    "COHORT_MIN_SIZE": int(os.environ.get("PALP_PEER_COHORT_MIN", 10)),
    "COHORT_RECLUSTER_DAYS": int(os.environ.get("PALP_PEER_RECLUSTER_DAYS", 7)),
    "COHORT_KMEANS_SEED": int(os.environ.get("PALP_PEER_KMEANS_SEED", 42)),
    # Benchmark
    "BENCHMARK_DEFAULT": False,
    "BENCHMARK_MIN_DAYS_AFTER_JOIN": int(
        os.environ.get("PALP_PEER_BENCHMARK_MIN_DAYS", 28)
    ),
    # Reciprocal matching
    "BUDDY_STRONG_WEAK_THRESHOLD": float(
        os.environ.get("PALP_PEER_BUDDY_THRESHOLD", 0.30)
    ),
    "BUDDY_REMATCH_DAYS": int(os.environ.get("PALP_PEER_REMATCH_DAYS", 14)),
    # Herd cluster detection (DBSCAN)
    "HERD_EPS": float(os.environ.get("PALP_PEER_HERD_EPS", 0.6)),
    "HERD_MIN_SAMPLES": int(os.environ.get("PALP_PEER_HERD_MIN_SAMPLES", 3)),
    "HERD_RISK_THRESHOLD": float(os.environ.get("PALP_PEER_HERD_RISK", 60.0)),
    "HERD_BEHAVIOR_WINDOW_DAYS": int(
        os.environ.get("PALP_PEER_HERD_WINDOW_DAYS", 14)
    ),
    # Frontier
    "FRONTIER_LOOKBACK_DAYS": int(
        os.environ.get("PALP_PEER_FRONTIER_LOOKBACK", 28)
    ),
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
    # NOTE: keep in sync with backend/privacy/constants.py::CONSENT_VERSION.
    # Bumped to 1.1 in v3 roadmap Phase 1 (behavioral_signals + cognitive_calibration).
    "CONSENT_VERSION": "1.1",
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
    # v3 roadmap — Phase 0 (sensitive infra surfaces)
    "/api/sessions/",
    "/api/causal/",
    "/api/fairness/",
    "/api/mlops/",
    # v3 roadmap — Phase 1
    "/api/signals/",
    "/api/risk/",
    "/api/adaptive/calibration/",
    # v3 roadmap — Phase 2
    "/api/goals/",
    # v3 roadmap — Phase 3
    "/api/peer/",
    # v3 roadmap — Phase 4
    "/api/coach/",
    "/api/emergency/",
    "/api/notifications/",
    # v3 roadmap — Phase 5
    "/api/dkt/",
    "/api/knowledge-graph/",
    "/api/bandit/",
    # v3 roadmap — Phase 6
    "/api/explain/",
    "/api/spacedrep/",
    "/api/privacy-dp/",
    "/api/copilot/",
    # v3 roadmap — Phase 7
    "/api/benchmarks/",
    "/api/research/",
    "/api/publication/",
    "/api/affect/",
]
