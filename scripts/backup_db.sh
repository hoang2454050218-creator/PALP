#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups}"
POSTGRES_USER="${POSTGRES_USER:-palp}"
POSTGRES_DB="${POSTGRES_DB:-palp}"
POSTGRES_HOST="${POSTGRES_HOST:-db}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/palp_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "{\"event\":\"backup_start\",\"timestamp\":\"$(date -Iseconds)\",\"target\":\"${BACKUP_FILE}\"}"

if pg_dump \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    "$POSTGRES_DB" | gzip > "$BACKUP_FILE"; then

    SIZE=$(stat -c%s "$BACKUP_FILE" 2>/dev/null || stat -f%z "$BACKUP_FILE" 2>/dev/null || echo "unknown")
    echo "{\"event\":\"backup_success\",\"file\":\"${BACKUP_FILE}\",\"size_bytes\":${SIZE}}"
else
    echo "{\"event\":\"backup_failed\",\"file\":\"${BACKUP_FILE}\"}" >&2
    exit 1
fi

DELETED=$(find "$BACKUP_DIR" -name "palp_*.sql.gz" -mtime +"$RETENTION_DAYS" -print -delete | wc -l)
echo "{\"event\":\"backup_cleanup\",\"deleted_count\":${DELETED},\"retention_days\":${RETENTION_DAYS}}"
