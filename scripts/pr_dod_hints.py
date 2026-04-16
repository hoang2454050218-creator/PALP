"""
PR Definition of Done — automated hints (non-blocking).

Compares base..HEAD and prints WARN for:
- API surface changes without docs touch
- API/views/serializers changes without negative-test signals in changed tests

Exit code is always 0 (hints only). For use in CI on pull_request.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Files that indicate contract / behavior docs should be reviewed
DOC_PATHS = (
    "docs/API.md",
    "docs/ARCHITECTURE.md",
    "docs/DATA_MODEL.md",
    "docs/DEPLOYMENT.md",
)

# Backend paths that often require API or schema docs
API_LIKE_PATTERNS = (
    r"backend/[^/]+/urls\.py$",
    r"backend/[^/]+/views\.py$",
    r"backend/[^/]+/serializers\.py$",
    r"backend/[^/]+/models\.py$",
    r"backend/[^/]+/permissions\.py$",
)

NEGATIVE_HINTS = re.compile(
    r"(401|403|404|400|422|"
    r"status_code\s*==\s*(400|401|403|404)|"
    r"assert\s+.*\.status_code|"
    r"invalid|unauthorized|forbidden|ValidationError|permission_denied|"
    r"pytest\.mark\.parametrize)",
    re.IGNORECASE,
)


def _git(args: list[str], cwd: str = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _list_changed_files(base_ref: str) -> list[str]:
    fetch = _git(["fetch", "origin", base_ref])
    if fetch.returncode != 0:
        print(f"[dod-hints] WARN: git fetch origin {base_ref} failed: {fetch.stderr.strip()}")
        return []
    diff = _git(["diff", "--name-only", f"origin/{base_ref}...HEAD"])
    if diff.returncode != 0:
        print(f"[dod-hints] WARN: git diff failed: {diff.stderr.strip()}")
        return []
    lines = [ln.strip() for ln in diff.stdout.splitlines() if ln.strip()]
    return lines


def _matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(p, path.replace("\\", "/")) for p in patterns)


def _is_test_file(path: str) -> bool:
    p = path.replace("\\", "/")
    return "/tests/" in p or "test_" in os.path.basename(p) or p.endswith("tests.py")


def _check_docs_with_api_changes(changed: list[str]) -> list[str]:
    warnings: list[str] = []
    api_touched = [f for f in changed if _matches_any(f, API_LIKE_PATTERNS)]
    doc_touched = [f for f in changed if f.replace("\\", "/") in DOC_PATHS]
    if api_touched and not doc_touched:
        warnings.append(
            "API/models/views/serializers/urls changed but no edit in docs/API.md, "
            "docs/ARCHITECTURE.md, docs/DATA_MODEL.md, or docs/DEPLOYMENT.md — "
            "confirm D10 (docs) if behavior contract changed."
        )
    return warnings


def _check_negative_tests(changed: list[str]) -> list[str]:
    warnings: list[str] = []
    api_touched = any(_matches_any(f, API_LIKE_PATTERNS) for f in changed)
    if not api_touched:
        return warnings

    test_files = [f for f in changed if _is_test_file(f) and f.endswith(".py")]
    if not test_files:
        warnings.append(
            "Backend API surface may have changed but no test files in this diff — "
            "confirm D2/D3/D4 (tests including negative cases)."
        )
        return warnings

    for tf in test_files:
        path = os.path.join(REPO_ROOT, tf)
        try:
            content = open(path, encoding="utf-8", errors="replace").read()
        except OSError as e:
            warnings.append(f"Could not read {tf}: {e}")
            continue
        if NEGATIVE_HINTS.search(content):
            return warnings

    warnings.append(
        "Changed test files do not show obvious negative/error assertions — "
        "confirm D4 (negative tests: 4xx, validation, RBAC)."
    )
    return warnings


def main() -> int:
    base = os.environ.get("GITHUB_BASE_REF", "main").replace("refs/heads/", "")
    event = os.environ.get("GITHUB_EVENT_NAME", "")

    if event and event != "pull_request":
        print(f"[dod-hints] SKIP: GITHUB_EVENT_NAME={event!r} (only pull_request uses hints)")
        return 0

    changed = _list_changed_files(base)
    if not changed:
        print(f"[dod-hints] No changed files vs origin/{base}...HEAD (or fetch failed).")
        return 0

    print(f"[dod-hints] Base: origin/{base}...HEAD ({len(changed)} files)")

    all_warns: list[str] = []
    all_warns.extend(_check_docs_with_api_changes(changed))
    all_warns.extend(_check_negative_tests(changed))

    if not all_warns:
        print("[dod-hints] OK: no automated warnings (still complete PR DoD checklist manually).")
        return 0

    for w in all_warns:
        print(f"[dod-hints] WARN: {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
