"""
PALP release operations helper: prints pre/post checklist (QA_STANDARD 17.2 / 17.3)
and optionally runs the automated release gate (scripts/release_gate.py).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PRE_RELEASE = """
=== 17.2 Pre-release checklist ===
[ ] Release notes drafted and linked to version tag
[ ] Migration plan reviewed (forward + backward compatibility)
[ ] Rollback plan documented (image tag + DB restore path)
[ ] Monitoring dashboard live (Grafana) and Sentry receiving events
[ ] Alert rules armed (queue depth, 5xx, Celery beat, backup age)
[ ] Backup verified fresh (timestamp within SLA)
[ ] Smoke test script ready: scripts/smoke_test.sh
[ ] Feature flags / kill-switches reviewed
[ ] Config parity staging vs prod checked (.env / secrets manager)
"""

POST_RELEASE = """
=== 17.3 Post-release checklist (first 30 minutes) ===
[ ] Smoke tests pass (health, auth optional, curriculum, dashboard alerts)
[ ] Core journeys pass (E2E or manual J1-J7 sample)
[ ] Error rate normal vs SLO (deep health / Sentry)
[ ] Event ingestion normal (metrics / spot-check EventLog)
[ ] Adaptive engine metrics normal (BKT / pathway latency)
[ ] Alert generation normal (no silent batch)
[ ] No data lag (Celery queue depth, analytics freshness)
[ ] Rollback decision window < 30 minutes (on-call + runbook)
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="PALP release checklist")
    parser.add_argument(
        "--phase",
        choices=("pre", "post", "both"),
        default="both",
        help="Which checklist to print",
    )
    parser.add_argument(
        "--run-gate",
        action="store_true",
        help="Run scripts/release_gate.py after printing (same flags as that script)",
    )
    parser.add_argument("--skip-tests", action="store_true", help="Passed to release_gate when --run-gate")
    args, rest = parser.parse_known_args()

    if args.phase in ("pre", "both"):
        print(PRE_RELEASE.strip())
    if args.phase in ("post", "both"):
        print(POST_RELEASE.strip())

    if args.run_gate:
        cmd = [sys.executable, str(ROOT / "scripts" / "release_gate.py")]
        if args.skip_tests:
            cmd.append("--skip-tests")
        cmd.extend(rest)
        raise SystemExit(subprocess.call(cmd, cwd=str(ROOT)))


if __name__ == "__main__":
    main()
