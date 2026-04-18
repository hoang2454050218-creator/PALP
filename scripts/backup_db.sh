#!/usr/bin/env bash
#
# PALP database backup with GPG encryption and optional off-site upload.
#
# Output layout:
#   ${BACKUP_DIR}/palp_<TIMESTAMP>.sql.gz           # raw dump (always)
#   ${BACKUP_DIR}/palp_<TIMESTAMP>.sql.gz.gpg       # encrypted (if GPG passphrase set)
#   ${BACKUP_DIR}/.last_backup_unix                  # sentinel: time.time() of latest success
#   ${BACKUP_DIR}/.last_backup_meta.json             # latest backup metadata for restore drill
#
# Environment variables:
#   POSTGRES_HOST / POSTGRES_PORT / POSTGRES_USER / POSTGRES_DB
#   PGPASSWORD                       (recommended over PGPASSFILE for containers)
#   BACKUP_DIR                       (default /backups)
#   BACKUP_RETENTION_DAYS            (default 7)
#   BACKUP_GPG_PASSPHRASE            (if set, encrypt with AES256; otherwise plaintext gzip)
#   BACKUP_S3_BUCKET                 (if set, upload via `aws s3 cp`)
#   BACKUP_S3_PREFIX                 (default "palp/db", appended to bucket)
#   BACKUP_S3_ENDPOINT               (optional, for S3-compatible providers like Backblaze B2)
#   AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY  (consumed by aws CLI)
#
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups}"
POSTGRES_USER="${POSTGRES_USER:-palp}"
POSTGRES_DB="${POSTGRES_DB:-palp}"
POSTGRES_HOST="${POSTGRES_HOST:-db}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
S3_PREFIX="${BACKUP_S3_PREFIX:-palp/db}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BASENAME="palp_${TIMESTAMP}.sql.gz"
RAW_FILE="${BACKUP_DIR}/${BASENAME}"
SENTINEL_FILE="${BACKUP_DIR}/.last_backup_unix"
META_FILE="${BACKUP_DIR}/.last_backup_meta.json"

mkdir -p "$BACKUP_DIR"

log_event() {
    local event="$1"; shift
    local extra="${1:-}"
    printf '{"event":"%s","timestamp":"%s","host":"%s","db":"%s"%s}\n' \
        "$event" "$(date -Iseconds)" "$POSTGRES_HOST" "$POSTGRES_DB" "$extra"
}

log_event "backup_start" ",\"target\":\"${RAW_FILE}\""

# Step 1: pg_dump | gzip
if ! pg_dump \
        --host "$POSTGRES_HOST" \
        --port "$POSTGRES_PORT" \
        --username "$POSTGRES_USER" \
        --no-owner --no-privileges \
        "$POSTGRES_DB" | gzip > "$RAW_FILE"; then
    log_event "backup_failed" ",\"stage\":\"pg_dump\",\"file\":\"${RAW_FILE}\"" >&2
    rm -f "$RAW_FILE"
    exit 1
fi

RAW_SIZE=$(stat -c%s "$RAW_FILE" 2>/dev/null || stat -f%z "$RAW_FILE" 2>/dev/null || echo 0)
ARTIFACT_FILE="$RAW_FILE"
ENCRYPTED=false

# Step 2: GPG encryption (optional but strongly recommended for off-site)
if [ -n "${BACKUP_GPG_PASSPHRASE:-}" ]; then
    ENCRYPTED_FILE="${RAW_FILE}.gpg"
    if printf '%s' "$BACKUP_GPG_PASSPHRASE" | gpg --batch --yes --pinentry-mode loopback \
            --passphrase-fd 0 \
            --symmetric --cipher-algo AES256 \
            --output "$ENCRYPTED_FILE" "$RAW_FILE"; then
        rm -f "$RAW_FILE"
        ARTIFACT_FILE="$ENCRYPTED_FILE"
        ENCRYPTED=true
        log_event "backup_encrypted" ",\"file\":\"${ENCRYPTED_FILE}\""
    else
        log_event "backup_encrypt_failed" ",\"file\":\"${RAW_FILE}\"" >&2
        exit 1
    fi
fi

ARTIFACT_SIZE=$(stat -c%s "$ARTIFACT_FILE" 2>/dev/null || stat -f%z "$ARTIFACT_FILE" 2>/dev/null || echo 0)

# Step 3: off-site upload (optional)
S3_URI=""
if [ -n "${BACKUP_S3_BUCKET:-}" ]; then
    if ! command -v aws >/dev/null 2>&1; then
        log_event "backup_s3_skipped" ",\"reason\":\"aws_cli_not_installed\"" >&2
    else
        S3_URI="s3://${BACKUP_S3_BUCKET}/${S3_PREFIX}/$(basename "$ARTIFACT_FILE")"
        AWS_ARGS=()
        if [ -n "${BACKUP_S3_ENDPOINT:-}" ]; then
            AWS_ARGS+=("--endpoint-url" "$BACKUP_S3_ENDPOINT")
        fi
        if aws s3 cp "${AWS_ARGS[@]}" "$ARTIFACT_FILE" "$S3_URI"; then
            log_event "backup_uploaded" ",\"s3_uri\":\"${S3_URI}\""
        else
            log_event "backup_upload_failed" ",\"s3_uri\":\"${S3_URI}\"" >&2
            # Off-site failure does not mark whole backup as failed; the local
            # copy is still valid. Surface as warning so monitoring can alert.
        fi
    fi
fi

# Step 4: sentinel + metadata for restore drill task
NOW_UNIX=$(date +%s)
echo "$NOW_UNIX" > "$SENTINEL_FILE"
cat > "$META_FILE" <<JSON
{
  "timestamp_unix": ${NOW_UNIX},
  "timestamp_iso": "$(date -Iseconds)",
  "artifact": "$(basename "$ARTIFACT_FILE")",
  "artifact_path": "${ARTIFACT_FILE}",
  "raw_size_bytes": ${RAW_SIZE},
  "artifact_size_bytes": ${ARTIFACT_SIZE},
  "encrypted": ${ENCRYPTED},
  "s3_uri": "${S3_URI}",
  "host": "${POSTGRES_HOST}",
  "db": "${POSTGRES_DB}"
}
JSON

log_event "backup_success" ",\"file\":\"${ARTIFACT_FILE}\",\"size_bytes\":${ARTIFACT_SIZE},\"encrypted\":${ENCRYPTED},\"s3_uri\":\"${S3_URI}\""

# Step 5: retention cleanup (local only -- S3 should use lifecycle policy)
DELETED=$(find "$BACKUP_DIR" -maxdepth 1 \
    \( -name "palp_*.sql.gz" -o -name "palp_*.sql.gz.gpg" \) \
    -mtime +"$RETENTION_DAYS" -print -delete | wc -l)
log_event "backup_cleanup" ",\"deleted_count\":${DELETED},\"retention_days\":${RETENTION_DAYS}"
