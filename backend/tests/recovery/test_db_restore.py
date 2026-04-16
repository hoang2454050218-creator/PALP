"""
Recovery test: Database backup/restore drill.

Simulates the full backup -> destroy -> restore -> verify cycle
from QA_STANDARD Section 9.2, using Django's dumpdata/loaddata.

Verifies that:
  - All tables restore with correct row counts
  - FK relationships remain intact
  - API endpoints respond correctly post-restore
  - Login works with restored credentials
  - MasteryState data matches pre-backup values
"""
import io
import json
import time

import pytest

from django.core.management import call_command

from accounts.models import User
from adaptive.models import MasteryState, TaskAttempt
from assessment.models import AssessmentSession, AssessmentResponse
from dashboard.models import Alert

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.recovery]


class TestBackupRestoreDrill:
    """Full backup -> destroy -> restore -> verify cycle."""

    def test_full_drill_row_counts(self, populated_db):
        expected = populated_db["counts"]

        dump_output = io.StringIO()
        call_command(
            "dumpdata",
            "--natural-foreign", "--natural-primary",
            "--indent=2",
            stdout=dump_output,
        )
        dump_json = dump_output.getvalue()
        assert len(dump_json) > 100

        call_command("flush", "--no-input")

        assert User.objects.count() == 0
        assert MasteryState.objects.count() == 0

        load_input = io.StringIO(dump_json)
        call_command("loaddata", "--format=json", "-", stdin=load_input)

        assert User.objects.count() == expected["users"]
        assert MasteryState.objects.count() == expected["mastery_states"]
        assert TaskAttempt.objects.count() == expected["task_attempts"]
        assert Alert.objects.count() == expected["alerts"]
        assert AssessmentSession.objects.count() == expected["assessment_sessions"]
        assert AssessmentResponse.objects.count() == expected["assessment_responses"]

    def test_mastery_data_integrity_after_restore(self, populated_db):
        original_states = {
            (ms.student_id, ms.concept_id): ms.p_mastery
            for ms in populated_db["mastery_states"]
        }

        dump_output = io.StringIO()
        call_command("dumpdata", "--natural-foreign", "--natural-primary", stdout=dump_output)
        dump_json = dump_output.getvalue()

        call_command("flush", "--no-input")
        call_command("loaddata", "--format=json", "-", stdin=io.StringIO(dump_json))

        for (sid, cid), expected_p in original_states.items():
            restored = MasteryState.objects.get(student_id=sid, concept_id=cid)
            assert restored.p_mastery == pytest.approx(expected_p)

    def test_fk_relationships_intact(self, populated_db):
        dump_output = io.StringIO()
        call_command("dumpdata", "--natural-foreign", "--natural-primary", stdout=dump_output)
        dump_json = dump_output.getvalue()

        call_command("flush", "--no-input")
        call_command("loaddata", "--format=json", "-", stdin=io.StringIO(dump_json))

        for alert in Alert.objects.all():
            assert alert.student is not None
            assert alert.student_class is not None

        for attempt in TaskAttempt.objects.all():
            assert attempt.student is not None
            assert attempt.task is not None

        for ms in MasteryState.objects.all():
            assert ms.student is not None
            assert ms.concept is not None


class TestPostRestoreAPIVerification:
    """API endpoints must function correctly after DB restore."""

    def test_health_endpoint_after_restore(self, populated_db, anon_api):
        dump_output = io.StringIO()
        call_command("dumpdata", "--natural-foreign", "--natural-primary", stdout=dump_output)
        dump_json = dump_output.getvalue()

        call_command("flush", "--no-input")
        call_command("loaddata", "--format=json", "-", stdin=io.StringIO(dump_json))

        resp = anon_api.get("/api/health/")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_login_works_after_restore(self, populated_db, anon_api):
        dump_output = io.StringIO()
        call_command("dumpdata", "--natural-foreign", "--natural-primary", stdout=dump_output)
        dump_json = dump_output.getvalue()

        call_command("flush", "--no-input")
        call_command("loaddata", "--format=json", "-", stdin=io.StringIO(dump_json))

        resp = anon_api.post(
            "/api/auth/login/",
            data={"username": "sv_rec_1", "password": "Str0ngP@ss!"},
        )
        assert resp.status_code == 200
        assert "access" in resp.json()


class TestRestoreTimeBudget:
    """Restore must complete within acceptable time budget."""

    def test_restore_under_time_limit(self, populated_db):
        dump_output = io.StringIO()
        call_command("dumpdata", "--natural-foreign", "--natural-primary", stdout=dump_output)
        dump_json = dump_output.getvalue()

        call_command("flush", "--no-input")

        t0 = time.monotonic()
        call_command("loaddata", "--format=json", "-", stdin=io.StringIO(dump_json))
        elapsed = time.monotonic() - t0

        assert elapsed < 60, f"Restore took {elapsed:.1f}s, budget is 60s for test data"
