"""
PALP Release Gate -- Go/No-Go automated checker.

Verifies the subset of Go/No-Go conditions (Section 13 of QA_STANDARD.md)
that can be programmatically checked. Outputs a structured report.

Usage:
    python scripts/release_gate.py [--format json|text] [--skip-tests]
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from enum import Enum

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "palp.settings.development")

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


class Status(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    MANUAL = "MANUAL"


@dataclass
class CheckResult:
    check_id: str
    name: str
    status: Status
    detail: str = ""
    elapsed_ms: int = 0


@dataclass
class GateReport:
    timestamp: str = ""
    no_go_results: list = field(default_factory=list)
    go_results: list = field(default_factory=list)
    overall: Status = Status.FAIL

    @property
    def no_go_passed(self) -> bool:
        return all(
            r.status in (Status.PASS, Status.MANUAL, Status.SKIP)
            for r in self.no_go_results
        )

    @property
    def go_passed(self) -> bool:
        return all(
            r.status in (Status.PASS, Status.MANUAL, Status.SKIP)
            for r in self.go_results
        )


def _run_pytest(marker_or_filter: str, label: str) -> CheckResult:
    """Run a pytest suite and return pass/fail."""
    start = time.monotonic()
    cmd = [
        sys.executable, "-m", "pytest",
        marker_or_filter,
        "--no-cov", "--no-header", "-q", "--tb=line",
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=BACKEND_DIR, timeout=300,
        )
        elapsed = int((time.monotonic() - start) * 1000)
        if result.returncode == 0:
            return CheckResult(label, label, Status.PASS, "All tests passed", elapsed)
        last_lines = result.stdout.strip().split("\n")[-3:]
        summary = " | ".join(last_lines)
        return CheckResult(label, label, Status.FAIL, summary, elapsed)
    except subprocess.TimeoutExpired:
        elapsed = int((time.monotonic() - start) * 1000)
        return CheckResult(label, label, Status.FAIL, "Timeout (>300s)", elapsed)
    except FileNotFoundError:
        return CheckResult(label, label, Status.SKIP, "pytest not found")


def _run_shell(cmd: list[str], cwd: str, timeout: int = 120) -> tuple[int, str]:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout,
        )
        output = (result.stdout + result.stderr).strip()
        return result.returncode, output
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return 1, str(exc)


# ---------------------------------------------------------------------------
# No-Go checks (NG-01 to NG-08)
# ---------------------------------------------------------------------------

def check_ng01_adaptive_rules(skip_tests: bool) -> CheckResult:
    if skip_tests:
        return CheckResult("NG-01", "Adaptive rules (BKT + pathway)", Status.SKIP, "--skip-tests")
    return _run_pytest("-k BKT or PATH", "NG-01")

def check_ng02_progress(skip_tests: bool) -> CheckResult:
    if skip_tests:
        return CheckResult("NG-02", "Progress update", Status.SKIP, "--skip-tests")
    return _run_pytest("-k SUBMIT or RETRY", "NG-02")

def check_ng03_dashboard_rbac(skip_tests: bool) -> CheckResult:
    if skip_tests:
        return CheckResult("NG-03", "Dashboard RBAC", Status.SKIP, "--skip-tests")
    return _run_pytest("-m security -k RBAC or ALERT", "NG-03")

def check_ng04_data_export(skip_tests: bool) -> CheckResult:
    if skip_tests:
        return CheckResult("NG-04", "Xoa/export du lieu", Status.SKIP, "--skip-tests")
    return _run_pytest("-k privacy or export or delete", "NG-04")

def check_ng05_etl(skip_tests: bool) -> CheckResult:
    if skip_tests:
        return CheckResult("NG-05", "ETL silent failure", Status.SKIP, "--skip-tests")
    return _run_pytest("-m data_qa -k ETL", "NG-05")

def check_ng06_core_events(skip_tests: bool) -> CheckResult:
    if skip_tests:
        return CheckResult("NG-06", "Event core", Status.SKIP, "--skip-tests")
    return _run_pytest("-k EVT", "NG-06")

def check_ng07_backup() -> CheckResult:
    return CheckResult(
        "NG-07", "Backup restore",
        Status.MANUAL, "Run backup/restore drill (QA_STANDARD Section 9.2)",
    )

def check_ng08_rollback() -> CheckResult:
    return CheckResult(
        "NG-08", "Rollback",
        Status.MANUAL, "Run rollback procedure test (QA_STANDARD Section 9.3)",
    )


# ---------------------------------------------------------------------------
# Product Correctness checks (AP-01 to AP-05) -- QA_STANDARD Section 1.4
# ---------------------------------------------------------------------------

def check_product_correctness(skip_tests: bool) -> CheckResult:
    if skip_tests:
        return CheckResult("AP", "Product correctness (5 anti-patterns)", Status.SKIP, "--skip-tests")
    return _run_pytest(
        "tests/integration/test_product_correctness.py",
        "AP",
    )

def check_data_cleaning(skip_tests: bool) -> CheckResult:
    if skip_tests:
        return CheckResult("DC", "Data cleaning pipeline (DC-01..06)", Status.SKIP, "--skip-tests")
    return _run_pytest("-m data_qa -k DC or cleaning", "DC")

def check_event_completeness(skip_tests: bool) -> CheckResult:
    if skip_tests:
        return CheckResult("EC", "Event completeness (EC-01..08)", Status.SKIP, "--skip-tests")
    return _run_pytest("-k EC or event_completeness", "EC")

def check_learning_integrity(skip_tests: bool) -> CheckResult:
    if skip_tests:
        return CheckResult("LI", "Learning integrity (LI-F01..F06)", Status.SKIP, "--skip-tests")
    return _run_pytest(
        "tests/integration/test_learning_integrity.py",
        "LI",
    )


# ---------------------------------------------------------------------------
# Go checks (G-01 to G-10)
# ---------------------------------------------------------------------------

def check_g01_core_flows(skip_tests: bool) -> CheckResult:
    if skip_tests:
        return CheckResult("G-01", "Core flows (E2E J1-J7)", Status.SKIP, "--skip-tests")
    start = time.monotonic()
    rc, output = _run_shell(["npm", "run", "test:e2e"], cwd=FRONTEND_DIR, timeout=600)
    elapsed = int((time.monotonic() - start) * 1000)
    if rc == 0:
        return CheckResult("G-01", "Core flows (E2E J1-J7)", Status.PASS, "All journeys passed", elapsed)
    last_lines = output.strip().split("\n")[-3:]
    return CheckResult("G-01", "Core flows (E2E J1-J7)", Status.FAIL, " | ".join(last_lines), elapsed)

def check_g02_bugs() -> CheckResult:
    return CheckResult(
        "G-02", "P0/P1 bugs = 0",
        Status.MANUAL, "Verify in bug tracker: 0 open P0, 0 open P1",
    )

def check_g03_security(skip_tests: bool) -> CheckResult:
    if skip_tests:
        return CheckResult("G-03", "Security high+ = 0", Status.SKIP, "--skip-tests")

    test_result = _run_pytest("-m security", "G-03-tests")

    start = time.monotonic()
    rc_pip, out_pip = _run_shell(
        [sys.executable, "-m", "pip_audit", "--strict", "--desc"],
        cwd=BACKEND_DIR, timeout=120,
    )
    rc_npm, out_npm = _run_shell(
        ["npm", "audit", "--audit-level=high"],
        cwd=FRONTEND_DIR, timeout=120,
    )
    elapsed = int((time.monotonic() - start) * 1000)

    parts = []
    combined_status = test_result.status

    if rc_pip != 0:
        combined_status = Status.FAIL
        parts.append(f"pip-audit: {out_pip[:200]}")
    if rc_npm != 0:
        combined_status = Status.FAIL
        parts.append(f"npm audit: {out_npm[:200]}")
    if test_result.status == Status.FAIL:
        parts.append(f"security tests: {test_result.detail}")

    detail = " | ".join(parts) if parts else "All security checks passed"
    return CheckResult("G-03", "Security high+ = 0", combined_status, detail, test_result.elapsed_ms + elapsed)

def check_g04_privacy(skip_tests: bool) -> CheckResult:
    if skip_tests:
        return CheckResult("G-04", "Privacy issues = 0", Status.SKIP, "--skip-tests")
    return _run_pytest("-k PRI or consent or privacy", "G-04")

def check_g05_data_corruption() -> CheckResult:
    """Check data integrity via Django ORM (DI-01 to DI-12, BP-01 to BP-07)."""
    try:
        import django
        django.setup()
        from django.db import connection

        checks_passed = 0
        checks_total = 0
        failures = []

        from adaptive.models import MasteryState, TaskAttempt
        from accounts.models import User
        from events.models import EventLog
        from dashboard.models import Alert

        # DI-01: Orphan MasteryState
        checks_total += 1
        orphan_mastery = MasteryState.objects.exclude(
            student_id__in=User.objects.values_list("id", flat=True)
        ).count()
        if orphan_mastery == 0:
            checks_passed += 1
        else:
            failures.append(f"DI-01: {orphan_mastery} orphan MasteryState")

        # DI-02: Orphan TaskAttempt
        checks_total += 1
        orphan_attempts = TaskAttempt.objects.exclude(
            student_id__in=User.objects.values_list("id", flat=True)
        ).count()
        if orphan_attempts == 0:
            checks_passed += 1
        else:
            failures.append(f"DI-02: {orphan_attempts} orphan TaskAttempt")

        # DI-03: Orphan Alert
        checks_total += 1
        orphan_alerts = Alert.objects.exclude(
            student_id__in=User.objects.values_list("id", flat=True)
        ).count()
        if orphan_alerts == 0:
            checks_passed += 1
        else:
            failures.append(f"DI-03: {orphan_alerts} orphan Alert")

        # DI-04: Duplicate MasteryState (unique_together enforced by DB)
        checks_total += 1
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT student_id, concept_id, COUNT(*) c "
                "FROM palp_mastery_state "
                "GROUP BY student_id, concept_id HAVING COUNT(*) > 1"
            )
            dupes = cursor.fetchall()
        if len(dupes) == 0:
            checks_passed += 1
        else:
            failures.append(f"DI-04: {len(dupes)} duplicate MasteryState")

        # DI-09: Assessment score in [0, 100]
        checks_total += 1
        from assessment.models import AssessmentSession
        bad_scores = AssessmentSession.objects.filter(
            status="completed"
        ).exclude(
            score__gte=0, score__lte=100
        ).count()
        if bad_scores == 0:
            checks_passed += 1
        else:
            failures.append(f"DI-09: {bad_scores} scores outside [0,100]")

        # DI-10: attempt_number > 0
        checks_total += 1
        bad_attempts = TaskAttempt.objects.filter(attempt_number__lte=0).count()
        if bad_attempts == 0:
            checks_passed += 1
        else:
            failures.append(f"DI-10: {bad_attempts} attempt_number <= 0")

        # DI-11: EventLog orphan actor
        checks_total += 1
        orphan_events = EventLog.objects.exclude(
            actor__isnull=True
        ).exclude(
            actor_id__in=User.objects.values_list("id", flat=True)
        ).count()
        if orphan_events == 0:
            checks_passed += 1
        else:
            failures.append(f"DI-11: {orphan_events} orphan EventLog actors")

        # BP-01 to BP-04: BKT parameter bounds [0, 1]
        checks_total += 1
        bad_bounds = MasteryState.objects.filter(
            p_mastery__lt=0
        ).union(MasteryState.objects.filter(
            p_mastery__gt=1
        )).union(MasteryState.objects.filter(
            p_guess__lt=0
        )).union(MasteryState.objects.filter(
            p_guess__gt=1
        )).union(MasteryState.objects.filter(
            p_slip__lt=0
        )).union(MasteryState.objects.filter(
            p_slip__gt=1
        )).union(MasteryState.objects.filter(
            p_transit__lt=0
        )).union(MasteryState.objects.filter(
            p_transit__gt=1
        )).count()
        if bad_bounds == 0:
            checks_passed += 1
        else:
            failures.append(f"BP-01..04: {bad_bounds} params outside [0,1]")

        # BP-05: P(guess) + P(slip) < 1.0
        checks_total += 1
        degenerate = 0
        for ms in MasteryState.objects.only("p_guess", "p_slip").iterator(chunk_size=500):
            if ms.p_guess + ms.p_slip >= 1.0:
                degenerate += 1
        if degenerate == 0:
            checks_passed += 1
        else:
            failures.append(f"BP-05: {degenerate} degenerate P(guess)+P(slip)>=1")

        # BP-07: No NaN/Infinity
        checks_total += 1
        nan_count = 0
        for ms in MasteryState.objects.only(
            "p_mastery", "p_guess", "p_slip", "p_transit"
        ).iterator(chunk_size=500):
            for val in (ms.p_mastery, ms.p_guess, ms.p_slip, ms.p_transit):
                if math.isnan(val) or math.isinf(val):
                    nan_count += 1
                    break
        if nan_count == 0:
            checks_passed += 1
        else:
            failures.append(f"BP-07: {nan_count} NaN/Infinity in BKT params")

        status = Status.PASS if checks_passed == checks_total else Status.FAIL
        detail = f"{checks_passed}/{checks_total} checks passed"
        if failures:
            detail += f" -- FAILURES: {'; '.join(failures)}"
        return CheckResult("G-05", "Data corruption = 0", status, detail)

    except Exception as exc:
        return CheckResult("G-05", "Data corruption = 0", Status.FAIL, f"Error: {exc}")


def check_g06_event_completeness() -> CheckResult:
    """Check all 8 core event types exist and required fields are non-null."""
    try:
        import django
        django.setup()
        from events.models import EventLog

        CORE_EVENTS = [
            "session_started", "session_ended", "assessment_completed",
            "micro_task_completed", "content_intervention", "gv_action_taken",
            "wellbeing_nudge_shown", "page_view",
        ]

        total = EventLog.objects.count()
        if total == 0:
            return CheckResult(
                "G-06", "Event completeness", Status.MANUAL,
                "No events in DB -- verify in staging/production",
            )

        missing_types = []
        for evt in CORE_EVENTS:
            if not EventLog.objects.filter(event_name=evt).exists():
                missing_types.append(evt)

        null_actor = EventLog.objects.filter(actor__isnull=True).exclude(
            actor_type="system"
        ).count()

        completeness = ((total - null_actor) / total * 100) if total > 0 else 0

        failures = []
        if missing_types:
            failures.append(f"Missing types: {', '.join(missing_types)}")
        if completeness < 99.5:
            failures.append(f"Completeness {completeness:.2f}% < 99.5%")

        status = Status.PASS if not failures else Status.FAIL
        detail = f"{len(CORE_EVENTS) - len(missing_types)}/8 types present, {completeness:.2f}% complete"
        if failures:
            detail += f" -- {'; '.join(failures)}"
        return CheckResult("G-06", f"Event completeness >= 99.5%", status, detail)

    except Exception as exc:
        return CheckResult("G-06", "Event completeness", Status.FAIL, f"Error: {exc}")


def check_g07_backup() -> CheckResult:
    return CheckResult(
        "G-07", "Backup restore",
        Status.MANUAL, "Run backup/restore drill (QA_STANDARD Section 9.2)",
    )

def check_g08_uat() -> CheckResult:
    return CheckResult(
        "G-08", "UAT >= 90% task success",
        Status.MANUAL, "Check UAT report (UAT_SCRIPT.md Section 6, EXIT-01)",
    )

def check_g09_monitoring() -> CheckResult:
    """Check monitoring endpoints are live."""
    try:
        import django
        django.setup()
        from django.conf import settings as django_settings

        checks = []

        sentry_dsn = getattr(django_settings, "SENTRY_DSN", os.environ.get("SENTRY_DSN", ""))
        if sentry_dsn:
            checks.append("Sentry DSN: configured")
        else:
            checks.append("Sentry DSN: MISSING")

        import requests
        health_url = os.environ.get("HEALTH_URL", "http://localhost:8000/api/health/")
        try:
            resp = requests.get(health_url, timeout=5)
            if resp.status_code == 200:
                checks.append(f"Health ({health_url}): OK")
            else:
                checks.append(f"Health ({health_url}): HTTP {resp.status_code}")
        except Exception:
            checks.append(f"Health ({health_url}): unreachable")

        has_fail = any("MISSING" in c or "unreachable" in c for c in checks)
        status = Status.FAIL if has_fail else Status.PASS
        return CheckResult("G-09", "Monitoring live + armed", status, " | ".join(checks))

    except ImportError:
        return CheckResult(
            "G-09", "Monitoring live + armed",
            Status.MANUAL, "Install 'requests' to enable auto-check, or verify manually",
        )
    except Exception as exc:
        return CheckResult("G-09", "Monitoring live + armed", Status.FAIL, f"Error: {exc}")


def check_g10_kpi() -> CheckResult:
    """Check all 5 KPIs are computable (non-null, non-NaN)."""
    try:
        import django
        django.setup()
        from analytics.services import generate_kpi_snapshot
        from accounts.models import StudentClass

        first_class = StudentClass.objects.first()
        if not first_class:
            return CheckResult(
                "G-10", "KPI 100% measurable",
                Status.MANUAL, "No classes in DB -- verify in staging/production",
            )

        kpi = generate_kpi_snapshot(first_class.id, week_number=0)

        kpi_fields = [
            ("mastery.avg_mastery", kpi.get("mastery", {}).get("avg_mastery")),
            ("micro_task_completion_rate", kpi.get("micro_task_completion_rate")),
            ("active_learning_time", kpi.get("active_learning_time")),
            ("gv_dashboard_usage", kpi.get("gv_dashboard_usage")),
            ("struggling_detection_time", kpi.get("struggling_detection_time")),
        ]

        missing = []
        for name, val in kpi_fields:
            if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
                missing.append(name)

        measured = len(kpi_fields) - len(missing)
        status = Status.PASS if measured == len(kpi_fields) else Status.FAIL
        detail = f"{measured}/{len(kpi_fields)} KPIs measurable"
        if missing:
            detail += f" -- Missing/NaN: {', '.join(missing)}"
        return CheckResult("G-10", "KPI 100% measurable", status, detail)

    except Exception as exc:
        return CheckResult("G-10", "KPI 100% measurable", Status.FAIL, f"Error: {exc}")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def run_gate(skip_tests: bool = False) -> GateReport:
    from datetime import datetime, timezone

    report = GateReport(timestamp=datetime.now(timezone.utc).isoformat())

    report.no_go_results = [
        check_ng01_adaptive_rules(skip_tests),
        check_ng02_progress(skip_tests),
        check_ng03_dashboard_rbac(skip_tests),
        check_ng04_data_export(skip_tests),
        check_ng05_etl(skip_tests),
        check_ng06_core_events(skip_tests),
        check_ng07_backup(),
        check_ng08_rollback(),
        check_product_correctness(skip_tests),
        check_learning_integrity(skip_tests),
    ]

    report.go_results = [
        check_g01_core_flows(skip_tests),
        check_g02_bugs(),
        check_g03_security(skip_tests),
        check_g04_privacy(skip_tests),
        check_g05_data_corruption(),
        check_g06_event_completeness(),
        check_g07_backup(),
        check_g08_uat(),
        check_g09_monitoring(),
        check_g10_kpi(),
        check_data_cleaning(skip_tests),
        check_event_completeness(skip_tests),
    ]

    if report.no_go_passed and report.go_passed:
        report.overall = Status.PASS
    else:
        report.overall = Status.FAIL

    return report


def format_text(report: GateReport) -> str:
    WIDTH = 78
    lines = [
        "=" * WIDTH,
        "PALP RELEASE GATE -- Go/No-Go Report".center(WIDTH),
        f"Timestamp: {report.timestamp}".center(WIDTH),
        "=" * WIDTH,
        "",
        ">>> NO-GO CHECKS (any FAIL = immediate No-Go) <<<",
        "-" * WIDTH,
    ]

    for r in report.no_go_results:
        icon = {"PASS": "[OK]", "FAIL": "[XX]", "SKIP": "[--]", "MANUAL": "[??]"}[r.status.value]
        lines.append(f"  {icon}  {r.check_id:8s}  {r.name}")
        if r.detail:
            lines.append(f"              {r.detail}")

    ng_pass = sum(1 for r in report.no_go_results if r.status == Status.PASS)
    ng_total = len(report.no_go_results)
    ng_manual = sum(1 for r in report.no_go_results if r.status == Status.MANUAL)
    lines.append("")
    lines.append(f"  No-Go result: {ng_pass}/{ng_total} PASS, {ng_manual} MANUAL")
    lines.append("")

    lines.append(">>> GO CONDITION CHECKS <<<")
    lines.append("-" * WIDTH)

    for r in report.go_results:
        icon = {"PASS": "[OK]", "FAIL": "[XX]", "SKIP": "[--]", "MANUAL": "[??]"}[r.status.value]
        elapsed_str = f" ({r.elapsed_ms}ms)" if r.elapsed_ms > 0 else ""
        lines.append(f"  {icon}  {r.check_id:8s}  {r.name}{elapsed_str}")
        if r.detail:
            lines.append(f"              {r.detail}")

    go_pass = sum(1 for r in report.go_results if r.status == Status.PASS)
    go_total = len(report.go_results)
    go_manual = sum(1 for r in report.go_results if r.status == Status.MANUAL)
    lines.append("")
    lines.append(f"  Go result: {go_pass}/{go_total} PASS, {go_manual} MANUAL")

    lines.append("")
    lines.append("=" * WIDTH)

    overall_icon = {"PASS": ">>> GO <<<", "FAIL": ">>> NO-GO <<<"}[report.overall.value]
    lines.append(f"  OVERALL: {overall_icon}")

    failed = [
        r for r in report.no_go_results + report.go_results
        if r.status == Status.FAIL
    ]
    manual = [
        r for r in report.no_go_results + report.go_results
        if r.status == Status.MANUAL
    ]
    if failed:
        lines.append("")
        lines.append("  BLOCKERS:")
        for r in failed:
            lines.append(f"    - {r.check_id}: {r.name} -- {r.detail}")
    if manual:
        lines.append("")
        lines.append("  MANUAL VERIFICATION REQUIRED:")
        for r in manual:
            lines.append(f"    - {r.check_id}: {r.name} -- {r.detail}")

    lines.append("=" * WIDTH)
    return "\n".join(lines)


def format_json(report: GateReport) -> str:
    data = {
        "timestamp": report.timestamp,
        "overall": report.overall.value,
        "no_go_checks": [
            {
                "id": r.check_id,
                "name": r.name,
                "status": r.status.value,
                "detail": r.detail,
                "elapsed_ms": r.elapsed_ms,
            }
            for r in report.no_go_results
        ],
        "go_checks": [
            {
                "id": r.check_id,
                "name": r.name,
                "status": r.status.value,
                "detail": r.detail,
                "elapsed_ms": r.elapsed_ms,
            }
            for r in report.go_results
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="PALP Release Gate -- Go/No-Go checker")
    parser.add_argument(
        "--format", choices=["text", "json"], default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--skip-tests", action="store_true",
        help="Skip pytest/E2E suites (only run DB and infra checks)",
    )
    args = parser.parse_args()

    report = run_gate(skip_tests=args.skip_tests)

    if args.format == "json":
        print(format_json(report))
    else:
        print(format_text(report))

    sys.exit(0 if report.overall == Status.PASS else 1)


if __name__ == "__main__":
    main()
