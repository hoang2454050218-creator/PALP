#!/usr/bin/env bash
# Post-deploy smoke checks (QA_STANDARD Section 11.6).
# Usage: BASE_URL=https://palp.example.com SMOKE_USER=... SMOKE_PASSWORD=... ./scripts/smoke_test.sh
# Exit 0 = pass; non-zero = fail (use for automated rollback).

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost}"
BASE_URL="${BASE_URL%/}"
CLASS_ID="${CLASS_ID:-1}"

echo "== PALP smoke test against ${BASE_URL} =="

fail() {
  echo "BLOCK: $1" >&2
  exit 1
}

code=$(curl -sS -o /tmp/health.json -w "%{http_code}" "${BASE_URL}/api/health/" || true)
if [[ "${code}" != "200" ]]; then
  fail "GET /api/health/ expected 200, got ${code}"
fi
grep -q '"status"' /tmp/health.json || fail "health JSON missing status"

if [[ -n "${SMOKE_USER:-}" && -n "${SMOKE_PASSWORD:-}" ]]; then
  code=$(curl -sS -o /tmp/login.json -w "%{http_code}" \
    -X POST "${BASE_URL}/api/auth/login/" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"${SMOKE_USER}\",\"password\":\"${SMOKE_PASSWORD}\"}" || true)
  if [[ "${code}" != "200" ]]; then
    fail "POST /api/auth/login/ expected 200, got ${code}"
  fi
else
  echo "Skipping login (set SMOKE_USER and SMOKE_PASSWORD to enable)"
fi

code=$(curl -sS -o /tmp/courses.json -w "%{http_code}" "${BASE_URL}/api/curriculum/courses/" || true)
if [[ "${code}" != "200" && "${code}" != "401" ]]; then
  fail "GET /api/curriculum/courses/ expected 200 or 401, got ${code}"
fi

code=$(curl -sS -o /tmp/alerts.json -w "%{http_code}" "${BASE_URL}/api/dashboard/alerts/?class_id=${CLASS_ID}" || true)
if [[ "${code}" != "200" && "${code}" != "401" && "${code}" != "403" ]]; then
  fail "GET /api/dashboard/alerts/ expected 200/401/403, got ${code}"
fi

echo "OK: smoke checks passed"
