#!/bin/bash
set -euo pipefail

# Production entrypoint for the PALP backend container.
# Responsibilities:
#   1. Apply DB migrations unless explicitly disabled (multi-replica deploys
#      should set RUN_MIGRATIONS_ON_STARTUP=false and run a one-off job).
#   2. Refresh static assets unless skipped (already baked at build time, but
#      a runtime refresh is convenient for hot-config swaps).
#   3. Hand off to the configured server. Default = gunicorn web server, but
#      compose can override with `command: celery ...` for worker containers
#      so the same image powers every role.

RUN_MIGRATIONS="${RUN_MIGRATIONS_ON_STARTUP:-true}"
RUN_COLLECTSTATIC="${RUN_COLLECTSTATIC_ON_STARTUP:-true}"

if [[ "${RUN_MIGRATIONS}" == "true" ]]; then
  echo "[entrypoint] Running database migrations..."
  python manage.py migrate --noinput
else
  echo "[entrypoint] Skipping migrations (RUN_MIGRATIONS_ON_STARTUP=false)."
fi

if [[ "${RUN_COLLECTSTATIC}" == "true" ]]; then
  echo "[entrypoint] Collecting static files..."
  python manage.py collectstatic --noinput
else
  echo "[entrypoint] Skipping collectstatic (RUN_COLLECTSTATIC_ON_STARTUP=false)."
fi

if [[ $# -gt 0 ]]; then
  echo "[entrypoint] Executing custom command: $*"
  exec "$@"
fi

echo "[entrypoint] Starting Gunicorn..."
exec gunicorn -c gunicorn.conf.py palp.wsgi:application
