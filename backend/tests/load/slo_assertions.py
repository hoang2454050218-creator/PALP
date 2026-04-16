"""
SLO assertion hooks for Locust load tests.

Called automatically via @events.quitting in locustfile.py.
Reads Locust stats at the end of the run and validates against PALP_SLO targets.
"""
import json
import logging
import time
from pathlib import Path

import requests

logger = logging.getLogger("palp.loadtest.slo")

SLO_P95_MS = {
    "/api/auth/login/":                          300,
    "/api/adaptive/submit/":                     1500,
    "/api/adaptive/pathway/[id]/":               1500,
    "/api/adaptive/mastery/":                    500,
    "/api/adaptive/next-task/[id]/":             1500,
    "/api/dashboard/class/[id]/overview/":       2000,
    "/api/dashboard/alerts/":                    800,
    "/api/dashboard/alerts/?severity=red":       800,
    "/api/dashboard/interventions/history/":     1500,
    "/api/assessment/my-sessions/":              800,
    "/api/assessment/sessions/[id]/answer/":     800,
    "/api/events/track/":                        300,
    "/api/analytics/kpi/[id]/":                  1500,
    "/api/analytics/reports/":                   1500,
    "/api/analytics/data-quality/":              1500,
    "/api/health/":                              100,
    "/api/health/ready/":                        300,
    "/api/health/deep/":                         500,
    "/api/wellbeing/check/":                     800,
}

ERROR_RATE_LIMIT = 0.5   # percent
QUEUE_DEPTH_WARN = 50


def check_slo_on_quit(environment):
    """Main entry point: invoked by locustfile @events.quitting listener."""
    report = _build_report(environment)
    _log_report(report)
    _fail_on_breach(environment, report)


def _build_report(environment):
    stats = environment.runner.stats
    total_reqs = stats.total.num_requests
    total_fails = stats.total.num_failures
    error_rate = (total_fails / total_reqs * 100) if total_reqs > 0 else 0.0

    latency_results = []
    for entry in stats.entries.values():
        name = entry.name
        p95 = entry.get_response_time_percentile(0.95) or 0
        p99 = entry.get_response_time_percentile(0.99) or 0
        slo = SLO_P95_MS.get(name)
        passed = p95 <= slo if slo else True
        latency_results.append({
            "endpoint": name,
            "p95_ms": round(p95, 1),
            "p99_ms": round(p99, 1),
            "slo_p95_ms": slo,
            "requests": entry.num_requests,
            "failures": entry.num_failures,
            "passed": passed,
        })

    queue_depth = _probe_queue_depth(environment)
    dashboard_stale = _check_dashboard_staleness(environment)

    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "total_requests": total_reqs,
        "total_failures": total_fails,
        "error_rate_percent": round(error_rate, 3),
        "error_rate_passed": error_rate <= ERROR_RATE_LIMIT,
        "latency": latency_results,
        "queue_depth": queue_depth,
        "dashboard_staleness": dashboard_stale,
        "overall_passed": (
            error_rate <= ERROR_RATE_LIMIT
            and all(r["passed"] for r in latency_results)
            and queue_depth.get("passed", True)
            and dashboard_stale.get("passed", True)
        ),
    }


def _probe_queue_depth(environment):
    """Hit /api/health/deep/ to read queue backlog depth."""
    host = environment.host or "http://localhost:8000"
    try:
        resp = requests.post(
            f"{host}/api/auth/login/",
            json={"username": "test_admin", "password": "testpass123"},
            timeout=5,
        )
        if resp.status_code != 200:
            return {"depth": -1, "passed": True, "error": "admin login failed"}
        token = resp.json().get("access", "")
        resp = requests.get(
            f"{host}/api/health/deep/",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            depth = data.get("components", {}).get("queue", {}).get("depth", 0)
            return {
                "depth": depth,
                "passed": depth < QUEUE_DEPTH_WARN,
                "status": data.get("components", {}).get("queue", {}).get("status"),
            }
        return {"depth": -1, "passed": True, "error": f"health {resp.status_code}"}
    except Exception as exc:
        return {"depth": -1, "passed": True, "error": str(exc)}


def _check_dashboard_staleness(environment):
    """
    Verify the lecturer dashboard is not stale beyond 1 refresh cycle.
    The dashboard caches for 60s (CACHE_TTL in dashboard/services.py).
    """
    host = environment.host or "http://localhost:8000"
    try:
        resp = requests.post(
            f"{host}/api/auth/login/",
            json={"username": "gv_test", "password": "testpass123"},
            timeout=5,
        )
        if resp.status_code != 200:
            return {"passed": True, "error": "lecturer login failed"}
        token = resp.json().get("access", "")

        t0 = time.monotonic()
        resp = requests.get(
            f"{host}/api/dashboard/class/1/overview/",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        latency_ms = (time.monotonic() - t0) * 1000

        if resp.status_code == 200:
            data = resp.json()
            cached_at = data.get("cached_at")
            return {
                "latency_ms": round(latency_ms, 1),
                "cached_at": cached_at,
                "passed": latency_ms < 3000,
            }
        return {"passed": True, "error": f"overview {resp.status_code}"}
    except Exception as exc:
        return {"passed": True, "error": str(exc)}


def _log_report(report):
    logger.info("=" * 72)
    logger.info("  PALP SLO REPORT")
    logger.info("=" * 72)
    logger.info(
        "  Total: %d requests, %d failures (%.3f%%)",
        report["total_requests"],
        report["total_failures"],
        report["error_rate_percent"],
    )
    logger.info(
        "  Error rate: %s",
        "PASS" if report["error_rate_passed"] else "FAIL",
    )
    logger.info("-" * 72)

    for r in sorted(report["latency"], key=lambda x: x["endpoint"]):
        status = "PASS" if r["passed"] else "FAIL"
        slo = r["slo_p95_ms"] or "n/a"
        logger.info(
            "  %-45s p95=%7.1fms  slo=%s  %s",
            r["endpoint"], r["p95_ms"], slo, status,
        )

    logger.info("-" * 72)
    q = report["queue_depth"]
    logger.info(
        "  Queue depth: %s  (depth=%s)  %s",
        q.get("status", "?"), q.get("depth", "?"),
        "PASS" if q.get("passed") else "FAIL",
    )
    d = report["dashboard_staleness"]
    logger.info(
        "  Dashboard staleness: latency=%sms  %s",
        d.get("latency_ms", "?"),
        "PASS" if d.get("passed") else "FAIL",
    )
    logger.info("=" * 72)
    logger.info(
        "  OVERALL: %s",
        "PASS" if report["overall_passed"] else "FAIL",
    )
    logger.info("=" * 72)

    report_dir = Path("reports")
    report_dir.mkdir(exist_ok=True)
    report_file = report_dir / f"slo_report_{int(time.time())}.json"
    report_file.write_text(json.dumps(report, indent=2, default=str))
    logger.info("  Report saved to %s", report_file)


def _fail_on_breach(environment, report):
    if not report["overall_passed"]:
        breaches = []
        if not report["error_rate_passed"]:
            breaches.append(
                f"Error rate {report['error_rate_percent']:.3f}% > {ERROR_RATE_LIMIT}%"
            )
        for r in report["latency"]:
            if not r["passed"]:
                breaches.append(
                    f"{r['endpoint']} p95={r['p95_ms']:.0f}ms > SLO {r['slo_p95_ms']}ms"
                )
        if not report["queue_depth"].get("passed", True):
            breaches.append(
                f"Queue depth {report['queue_depth']['depth']} >= {QUEUE_DEPTH_WARN}"
            )
        if not report["dashboard_staleness"].get("passed", True):
            breaches.append("Dashboard stale beyond 1 refresh cycle")

        environment.process_exit_code = 1
        logger.error("SLO BREACHES: %s", "; ".join(breaches))
