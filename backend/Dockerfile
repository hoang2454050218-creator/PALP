# syntax=docker/dockerfile:1.7

# ---------- Stage 1: builder ----------
# Builds wheels with full toolchain so the runtime image stays minimal.
# renovate: datasource=docker depName=python versioning=docker
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt


# ---------- Stage 2: runtime ----------
# renovate: datasource=docker depName=python versioning=docker
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    APP_HOME=/app \
    APP_USER=palp \
    APP_UID=1000 \
    APP_GID=1000

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        postgresql-client \
        gnupg \
        awscli \
        curl \
        ca-certificates \
        tini \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid ${APP_GID} ${APP_USER} \
    && useradd  --system --uid ${APP_UID} --gid ${APP_GID} \
                --home ${APP_HOME} --shell /usr/sbin/nologin ${APP_USER}

WORKDIR ${APP_HOME}

COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

COPY --chown=${APP_USER}:${APP_USER} . .

RUN mkdir -p ${APP_HOME}/staticfiles ${APP_HOME}/media \
    && chown -R ${APP_USER}:${APP_USER} ${APP_HOME} \
    && chmod +x entrypoint.prod.sh \
    && DJANGO_SETTINGS_MODULE=palp.settings.base \
       python manage.py collectstatic --noinput \
    || (echo "[Dockerfile] collectstatic failed - check STATIC_ROOT/STATIC_URL"; exit 1)

USER ${APP_USER}

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health/ || exit 1

# tini reaps zombies and forwards signals so gunicorn workers shut down cleanly.
# entrypoint.prod.sh is the canonical startup; pass a custom argv to override
# (e.g. `command: ["celery", "-A", "palp", "worker"]` in docker-compose).
ENTRYPOINT ["/usr/bin/tini", "--", "./entrypoint.prod.sh"]
CMD []
