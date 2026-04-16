import logging
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

logger = logging.getLogger("palp")

QUERY_BUDGET_MS = 500

CORE_QUERIES = [
    {
        "name": "dashboard_alerts_by_class",
        "description": "Lecturer: active alerts for a class",
        "sql": """
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT a.id, a.severity, a.trigger_type, a.reason, a.created_at
            FROM palp_alert a
            WHERE a.student_class_id = 1
              AND a.status = 'active'
            ORDER BY a.created_at DESC
            LIMIT 50;
        """,
    },
    {
        "name": "dashboard_alerts_by_student",
        "description": "Dashboard: filter alerts by student + severity",
        "sql": """
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT a.id, a.severity, a.status, a.trigger_type
            FROM palp_alert a
            WHERE a.student_id = 1
              AND a.status = 'active'
              AND a.severity = 'red'
            ORDER BY a.created_at DESC;
        """,
    },
    {
        "name": "active_assessment_session",
        "description": "Check for active session (canonical record)",
        "sql": """
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT s.id, s.status, s.started_at
            FROM palp_assessment_session s
            WHERE s.student_id = 1
              AND s.assessment_id = 1
              AND s.status = 'in_progress';
        """,
    },
    {
        "name": "mastery_states_for_student",
        "description": "Pathway: all mastery states for a student",
        "sql": """
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT m.id, m.p_mastery, m.concept_id, m.last_updated
            FROM palp_mastery_state m
            WHERE m.student_id = 1
            ORDER BY m.last_updated DESC;
        """,
    },
    {
        "name": "latest_task_attempt",
        "description": "Student flow: latest attempt per task",
        "sql": """
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT t.id, t.score, t.is_correct, t.attempt_number
            FROM palp_task_attempt t
            WHERE t.student_id = 1
              AND t.task_id = 1
            ORDER BY t.created_at DESC
            LIMIT 1;
        """,
    },
    {
        "name": "recent_student_activity",
        "description": "Early warning: recent activity for a student",
        "sql": """
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT t.id, t.task_id, t.created_at
            FROM palp_task_attempt t
            WHERE t.student_id = 1
            ORDER BY t.created_at DESC
            LIMIT 20;
        """,
    },
    {
        "name": "event_log_by_actor",
        "description": "Events: query by actor and event type",
        "sql": """
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT e.id, e.event_name, e.timestamp_utc
            FROM palp_event_log e
            WHERE e.actor_id = 1
              AND e.event_name = 'micro_task_completed'
            ORDER BY e.timestamp_utc DESC
            LIMIT 50;
        """,
    },
    {
        "name": "event_log_by_session",
        "description": "Events: timeline for a session",
        "sql": """
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT e.id, e.event_name, e.timestamp_utc
            FROM palp_event_log e
            WHERE e.session_id = 'test-session-id'
            ORDER BY e.timestamp_utc ASC;
        """,
    },
    {
        "name": "nudge_history",
        "description": "Wellbeing: nudge history for a student",
        "sql": """
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT n.id, n.nudge_type, n.response, n.created_at
            FROM palp_wellbeing_nudge n
            WHERE n.student_id = 1
            ORDER BY n.created_at DESC
            LIMIT 20;
        """,
    },
    {
        "name": "consent_latest",
        "description": "Privacy: latest consent per purpose for a user",
        "sql": """
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT c.id, c.purpose, c.granted, c.created_at
            FROM palp_consent_record c
            WHERE c.user_id = 1
            ORDER BY c.created_at DESC
            LIMIT 10;
        """,
    },
]


class Command(BaseCommand):
    help = "Run EXPLAIN ANALYZE on core queries and verify index usage"

    def add_arguments(self, parser):
        parser.add_argument(
            "--fail-on-seqscan",
            action="store_true",
            help="Exit with error if any query uses Seq Scan on a table with > 1000 rows",
        )
        parser.add_argument(
            "--budget-ms",
            type=int,
            default=QUERY_BUDGET_MS,
            help=f"Max execution time in ms per query (default: {QUERY_BUDGET_MS})",
        )

    def handle(self, *args, **options):
        fail_on_seqscan = options["fail_on_seqscan"]
        budget_ms = options["budget_ms"]
        failures = []
        results = []

        self.stdout.write(self.style.MIGRATE_HEADING("PALP Index Benchmark"))
        self.stdout.write(f"Budget: {budget_ms}ms per query\n")

        for query_def in CORE_QUERIES:
            name = query_def["name"]
            description = query_def["description"]
            sql = query_def["sql"]

            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"  {name}: {description}")
            self.stdout.write(f"{'='*60}")

            try:
                start = time.perf_counter()
                with connection.cursor() as cursor:
                    cursor.execute(sql)
                    plan_rows = cursor.fetchall()
                elapsed_ms = (time.perf_counter() - start) * 1000

                plan = plan_rows[0][0] if plan_rows else []
                plan_node = plan[0] if plan else {}
                execution_time = plan_node.get("Execution Time", 0)
                planning_time = plan_node.get("Planning Time", 0)
                top_node = plan_node.get("Plan", {})
                node_type = top_node.get("Node Type", "Unknown")

                uses_seqscan = self._check_seqscan(top_node)
                over_budget = execution_time > budget_ms

                status = "PASS"
                if over_budget:
                    status = "SLOW"
                    failures.append(f"{name}: {execution_time:.1f}ms > {budget_ms}ms budget")
                if uses_seqscan and fail_on_seqscan:
                    status = "SEQSCAN"
                    failures.append(f"{name}: uses Seq Scan")

                color = self.style.SUCCESS if status == "PASS" else self.style.ERROR
                self.stdout.write(f"  Plan:      {node_type}")
                self.stdout.write(f"  Planning:  {planning_time:.2f}ms")
                self.stdout.write(f"  Execution: {execution_time:.2f}ms")
                self.stdout.write(f"  Seq Scan:  {'YES' if uses_seqscan else 'no'}")
                self.stdout.write(color(f"  Result:    [{status}]"))

                results.append({
                    "name": name,
                    "execution_ms": execution_time,
                    "planning_ms": planning_time,
                    "node_type": node_type,
                    "seq_scan": uses_seqscan,
                    "status": status,
                })

            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"  ERROR: {exc}"))
                failures.append(f"{name}: {exc}")

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.MIGRATE_HEADING("Summary"))
        passed = sum(1 for r in results if r["status"] == "PASS")
        total = len(CORE_QUERIES)
        self.stdout.write(f"  {passed}/{total} queries passed")

        if failures:
            self.stdout.write(self.style.ERROR("\nFailures:"))
            for f in failures:
                self.stdout.write(self.style.ERROR(f"  - {f}"))
            raise CommandError(f"{len(failures)} query benchmark(s) failed")

        self.stdout.write(self.style.SUCCESS("\nAll benchmarks passed."))

    def _check_seqscan(self, node):
        if not isinstance(node, dict):
            return False
        if node.get("Node Type") == "Seq Scan":
            actual_rows = node.get("Actual Rows", 0)
            if actual_rows > 1000:
                return True
        for child in node.get("Plans", []):
            if self._check_seqscan(child):
                return True
        return False
