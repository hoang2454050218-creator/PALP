"""
Recovery test: Release rollback feasibility.

Verifies that:
  - A database state change (simulating a new release) can be fully reverted
  - Data checksums match pre-rollback state
  - API endpoints respond correctly after rollback
  - The entire rollback completes within the 15-minute budget
"""
import hashlib
import io
import json
import time

import pytest

from django.core.management import call_command
from django.db import connection

from accounts.models import User
from adaptive.models import MasteryState, TaskAttempt
from assessment.models import AssessmentSession
from dashboard.models import Alert

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.recovery]

ROLLBACK_BUDGET_SECONDS = 900  # 15 minutes


def _snapshot_counts():
    return {
        "users": User.objects.count(),
        "mastery_states": MasteryState.objects.count(),
        "task_attempts": TaskAttempt.objects.count(),
        "alerts": Alert.objects.count(),
        "assessment_sessions": AssessmentSession.objects.count(),
    }


def _mastery_checksum():
    rows = MasteryState.objects.values_list(
        "student_id", "concept_id", "p_mastery", "attempt_count", "correct_count",
    ).order_by("student_id", "concept_id")
    h = hashlib.sha256()
    for row in rows:
        h.update(str(row).encode())
    return h.hexdigest()


class TestRollbackFeasibility:
    """Simulate release -> verify -> rollback -> verify cycle."""

    def test_full_rollback_cycle(self, populated_db, anon_api):
        t_start = time.monotonic()

        pre_counts = _snapshot_counts()
        pre_checksum = _mastery_checksum()

        dump_output = io.StringIO()
        call_command(
            "dumpdata", "--natural-foreign", "--natural-primary",
            stdout=dump_output,
        )
        backup_json = dump_output.getvalue()

        self._simulate_new_release(populated_db)

        post_release_counts = _snapshot_counts()
        assert post_release_counts != pre_counts

        call_command("flush", "--no-input")
        call_command(
            "loaddata", "--format=json", "-",
            stdin=io.StringIO(backup_json),
        )

        post_rollback_counts = _snapshot_counts()
        post_rollback_checksum = _mastery_checksum()

        assert post_rollback_counts == pre_counts
        assert post_rollback_checksum == pre_checksum

        resp = anon_api.get("/api/health/")
        assert resp.status_code == 200

        elapsed = time.monotonic() - t_start
        assert elapsed < ROLLBACK_BUDGET_SECONDS, (
            f"Rollback took {elapsed:.1f}s, budget is {ROLLBACK_BUDGET_SECONDS}s"
        )

    def test_api_functional_after_rollback(self, populated_db, anon_api):
        dump_output = io.StringIO()
        call_command(
            "dumpdata", "--natural-foreign", "--natural-primary",
            stdout=dump_output,
        )
        backup_json = dump_output.getvalue()

        self._simulate_new_release(populated_db)

        call_command("flush", "--no-input")
        call_command(
            "loaddata", "--format=json", "-",
            stdin=io.StringIO(backup_json),
        )

        resp = anon_api.post(
            "/api/auth/login/",
            data={"username": "sv_rec_1", "password": "Str0ngP@ss!"},
        )
        assert resp.status_code == 200

    def test_celery_tasks_run_after_rollback(self, populated_db):
        from analytics.tasks import run_nightly_early_warnings

        dump_output = io.StringIO()
        call_command(
            "dumpdata", "--natural-foreign", "--natural-primary",
            stdout=dump_output,
        )
        backup_json = dump_output.getvalue()

        self._simulate_new_release(populated_db)

        call_command("flush", "--no-input")
        call_command(
            "loaddata", "--format=json", "-",
            stdin=io.StringIO(backup_json),
        )

        result = run_nightly_early_warnings()
        assert isinstance(result, int)

    @staticmethod
    def _simulate_new_release(populated_db):
        """Mutate the DB to simulate changes from a new release deployment."""
        extra_student = User.objects.create_user(
            username="sv_new_release", password="NewP@ss1!",
            role=User.Role.STUDENT, student_id="22KT9999",
        )

        for ms in MasteryState.objects.all()[:3]:
            ms.p_mastery = min(0.99, ms.p_mastery + 0.1)
            ms.save()

        Alert.objects.create(
            student=populated_db["students"][0],
            student_class=populated_db["student_class"],
            severity=Alert.Severity.YELLOW,
            trigger_type=Alert.TriggerType.MILESTONE_LAG,
            reason="Simulated new-release alert",
            suggested_action="Test",
        )


class TestRollbackTimeBudget:
    """Rollback must complete within the 15-minute SLA."""

    def test_rollback_time_acceptable(self, populated_db):
        dump_output = io.StringIO()
        call_command(
            "dumpdata", "--natural-foreign", "--natural-primary",
            stdout=dump_output,
        )
        backup_json = dump_output.getvalue()

        call_command("flush", "--no-input")

        t0 = time.monotonic()
        call_command(
            "loaddata", "--format=json", "-",
            stdin=io.StringIO(backup_json),
        )
        elapsed = time.monotonic() - t0

        assert elapsed < 120, (
            f"Restore-only phase took {elapsed:.1f}s, expected < 120s for test data"
        )
