#!/usr/bin/env python
"""
CLI wrapper for PALP load test scenarios.

Usage:
    python -m tests.load.run_load --scenario stress
    python -m tests.load.run_load --scenario soak  --host http://staging:8000
    python -m tests.load.run_load --scenario spike
    python -m tests.load.run_load --scenario normal

Scenarios:
    normal   LT-01/02 -- 50-100 users, 22 min
    stress   LT-03    -- 200 users, 15 min
    soak     LT-05    -- 200 users, 30 min
    spike    LT-04    -- 200 -> 300 users burst, 16 min

Exit code 0 = SLO pass, 1 = SLO breach.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

SCENARIO_SHAPES = {
    "normal": "NormalLoadShape",
    "stress": "StressShape",
    "soak": "SoakShape",
    "spike": "SpikeShape",
}

LOAD_DIR = Path(__file__).resolve().parent
REPORTS_DIR = Path("reports")


def main():
    parser = argparse.ArgumentParser(description="PALP load test runner")
    parser.add_argument(
        "--scenario",
        choices=list(SCENARIO_SHAPES.keys()),
        default="stress",
        help="Test scenario to run (default: stress)",
    )
    parser.add_argument(
        "--host",
        default="http://localhost:8000",
        help="Target host (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--csv-prefix",
        default=None,
        help="CSV report prefix (default: reports/<scenario>_<timestamp>)",
    )
    parser.add_argument(
        "--html",
        default=None,
        help="HTML report path",
    )
    parser.add_argument(
        "--memory-watch",
        action="store_true",
        help="Log target process memory via /api/health/deep/ during run",
    )
    args = parser.parse_args()

    REPORTS_DIR.mkdir(exist_ok=True)
    ts = int(time.time())
    csv_prefix = args.csv_prefix or str(REPORTS_DIR / f"{args.scenario}_{ts}")
    html_path = args.html or str(REPORTS_DIR / f"{args.scenario}_{ts}.html")

    locustfile = str(LOAD_DIR / "locustfile.py")
    shapefile = str(LOAD_DIR / "shapes.py")

    cmd = [
        sys.executable, "-m", "locust",
        "-f", f"{locustfile},{shapefile}",
        "--host", args.host,
        "--headless",
        "--csv", csv_prefix,
        "--html", html_path,
        "--loglevel", "INFO",
        "--class-picker",
    ]

    shape_class = SCENARIO_SHAPES[args.scenario]
    env = {"LOCUST_SHAPE": shape_class}

    print(f"[PALP] Running {args.scenario} load test ({shape_class})")
    print(f"[PALP] Target:  {args.host}")
    print(f"[PALP] Reports: {csv_prefix}*.csv, {html_path}")
    print(f"[PALP] Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, env={**_get_env(), **env})

    slo_report = _find_latest_slo_report()
    if slo_report:
        print(f"\n[PALP] SLO report: {slo_report}")
        data = json.loads(slo_report.read_text())
        if data.get("overall_passed"):
            print("[PALP] RESULT: ALL SLO TARGETS MET")
        else:
            print("[PALP] RESULT: SLO BREACH DETECTED")
    else:
        print("[PALP] WARNING: No SLO report found")

    return result.returncode


def _get_env():
    import os
    return dict(os.environ)


def _find_latest_slo_report():
    reports = sorted(REPORTS_DIR.glob("slo_report_*.json"), reverse=True)
    return reports[0] if reports else None


if __name__ == "__main__":
    sys.exit(main())
