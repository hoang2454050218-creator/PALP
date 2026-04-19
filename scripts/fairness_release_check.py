#!/usr/bin/env python
"""
CI gate: fail the release if any production model has an open fairness violation.

Reads the latest ``FairnessAudit`` row per ``target_name`` and exits non-zero
if any of them are ``passed=False``. Designed to be invoked from CI:

    python scripts/fairness_release_check.py

Exit codes:
    0 = all production-relevant models pass
    1 = at least one model fails the gate
    2 = unexpected error (no audits found, DB unreachable, etc.)
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict


def main() -> int:
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        os.environ.get("DJANGO_SETTINGS_MODULE", "palp.settings.development"),
    )
    import django

    django.setup()

    from fairness.models import FairnessAudit

    audits = (
        FairnessAudit.objects.all()
        .order_by("target_name", "-created_at")
        .values("target_name", "passed", "violations", "created_at", "kind")
    )
    if not audits:
        print(
            "[fairness-gate] No fairness audits found. "
            "Production models must have at least one audit before release.",
            file=sys.stderr,
        )
        return 2

    # Use the most recent audit per target.
    latest_by_target: dict[str, dict] = {}
    for row in audits:
        if row["target_name"] not in latest_by_target:
            latest_by_target[row["target_name"]] = row

    failures: list[dict] = [r for r in latest_by_target.values() if not r["passed"]]

    if failures:
        print("[fairness-gate] FAIL — the following models have open violations:")
        grouped = defaultdict(list)
        for row in failures:
            for v in row["violations"]:
                grouped[row["target_name"]].append(v)
        for target, vlist in grouped.items():
            print(f"  - {target}:")
            for v in vlist:
                print(f"      * {v}")
        print()
        print("Resolve violations or document an explicit waiver in the audit notes "
              "before re-running this gate.")
        return 1

    print(f"[fairness-gate] PASS — {len(latest_by_target)} models reviewed, all clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
