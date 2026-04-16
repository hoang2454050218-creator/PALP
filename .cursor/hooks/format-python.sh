#!/bin/bash
input=$(cat)
file_path=$(echo "$input" | python3 -c "import sys,json; print(json.load(sys.stdin).get('path',''))" 2>/dev/null)

if [ -z "$file_path" ]; then
  exit 0
fi

if ! command -v ruff &>/dev/null; then
  exit 0
fi

ruff format --quiet "$file_path" 2>/dev/null
ruff check --fix --quiet "$file_path" 2>/dev/null

exit 0
