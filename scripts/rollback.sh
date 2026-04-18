#!/usr/bin/env bash
#
# PALP one-shot rollback.
#
# Usage: scripts/rollback.sh <previous_tag>
# Example: scripts/rollback.sh abc1234
#
# Switches the Nginx upstream back to the previous container set, expected
# to still be alive on the host (blue-green pair). If both colors are gone
# (catastrophic deploy), pull image by tag and recreate.
#
set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "usage: scripts/rollback.sh <previous_tag>"
    echo
    echo "available recent tags on this host:"
    docker images --filter=reference='ghcr.io/*/palp/backend' --format '  {{.Tag}}\t{{.CreatedAt}}'
    exit 1
fi

TAG="$1"
COMPOSE_FILE="${COMPOSE_FILE:-/opt/palp/docker-compose.prod.yml}"
NGINX_CONF="${NGINX_CONF:-/opt/palp/nginx/nginx.conf}"

log() {
    printf '{"event":"rollback","ts":"%s","tag":"%s","msg":"%s"}\n' \
        "$(date -Iseconds)" "$TAG" "$1"
}

log "Starting rollback to tag $TAG"

# 1. Try blue-green switch first (zero-downtime)
if docker ps --format '{{.Names}}' | grep -q palp-blue_backend; then
    log "Found palp-blue_backend running -- switching upstream"
    sed -i 's|server palp-green_backend_1:8000|server palp-blue_backend_1:8000|g' "$NGINX_CONF"
    docker compose -f "$COMPOSE_FILE" exec nginx nginx -s reload
    log "Upstream switched. Inspect logs: docker logs palp-blue_backend_1"
    exit 0
fi

# 2. Pull image by tag and recreate
log "Blue not running -- pulling tag $TAG and recreating"
export PALP_IMAGE_TAG="$TAG"
docker compose -f "$COMPOSE_FILE" pull backend frontend
docker compose -f "$COMPOSE_FILE" up -d --no-deps --force-recreate backend frontend

# 3. Wait for healthcheck
for i in {1..30}; do
    status=$(docker inspect --format='{{.State.Health.Status}}' palp-backend-1 2>/dev/null || echo "starting")
    if [[ "$status" == "healthy" ]]; then
        log "Rollback complete -- backend healthy"
        exit 0
    fi
    sleep 2
done

log "ERROR: backend did not become healthy after rollback. Check 'docker logs palp-backend-1'"
exit 1
