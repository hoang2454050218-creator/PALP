#!/usr/bin/env bash
# Auto-sync .ruler/ -> all agent configs whenever a rule/skill/config file is
# edited inside Cursor. Mirrors the pre-commit hook so the agent context is
# always live without waiting for the next commit.
#
# Receives Cursor hook JSON on stdin; we only need the file path.

set -euo pipefail

input=$(cat)
file_path=$(echo "$input" | python3 -c "import sys,json; print(json.load(sys.stdin).get('path',''))" 2>/dev/null || true)

if [[ -z "$file_path" ]]; then
    exit 0
fi

# Only react to .ruler/ source files. The matcher already filters but we
# double-check here so manual hook invocations stay safe.
case "$file_path" in
    *.ruler/* | *.ruler\\* ) ;;
    *) exit 0 ;;
esac

if ! command -v ruler >/dev/null 2>&1 && ! command -v npx >/dev/null 2>&1; then
    exit 0
fi

if command -v ruler >/dev/null 2>&1; then
    ruler apply --no-gitignore --no-backup --no-skills >/dev/null 2>&1 || true
else
    npx -y @intellectronica/ruler apply --no-gitignore --no-backup --no-skills >/dev/null 2>&1 || true
fi

exit 0
