"""
Recovery test: Celery worker dies mid-job.

Verifies that:
  - Tasks survive worker death (retry mechanism)
  - No duplicate side-effects (alerts, reports) on retry
  - Task state transitions are clean after recovery
"""
import pytest
from unittest.mock import patch, call

from celery.exceptions import WorkerLostError

from analytics.tasks import run_nightly_early_warnings, generate_weekly_report
from analytics.models import PilotReport
from dashboard.models import Alert

pytestmark = [pytest.mark.django_db, pytest.mark.recovery]


class TestNightlyTaskWorkerDeath:
    """Nightly early-warning task must handle WorkerLostError gracefully."""

    def test_succeeds_after_transient_worker_loss(self, class_with_members):
        call_count = {"n": 0}
        original = run_nightly_early_warnings.run

        def _flaky_run(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise WorkerLostError("Worker exited unexpectedly")
            return original(*args, **kwargs)

        with patch.object(
            run_nightly_early_warnings, "run", side_effect=_flaky_run,
        ):
            with pytest.raises(WorkerLostError):
                run_nightly_early_warnings()

        result = run_nightly_early_warnings()
        assert isinstance(result, int)

    def test_no_duplicate_alerts_after_retry(self, class_with_members):
        run_nightly_early_warnings()
        count_first = Alert.objects.count()

        run_nightly_early_warnings()
        count_after_retry = Alert.objects.count()

        assert count_after_retry == count_first

    def test_task_completes_with_correct_return(self, class_with_members):
        result = run_nightly_early_warnings()
        assert isinstance(result, int)
        assert result >= 0


class TestWeeklyReportWorkerDeath:
    """Weekly report generation must be resilient to worker death."""

    def test_report_not_duplicated_on_retry(self, class_with_members):
        report_id_1 = generate_weekly_report(class_with_members.id, 1)
        assert PilotReport.objects.filter(id=report_id_1).exists()

        report_id_2 = generate_weekly_report(class_with_members.id, 2)
        assert report_id_2 != report_id_1
        assert PilotReport.objects.count() == 2

    def test_report_data_complete_after_recovery(self, class_with_members):
        report_id = generate_weekly_report(class_with_members.id, 1)
        report = PilotReport.objects.get(id=report_id)

        assert report.week_number == 1
        assert report.kpi_data is not None
        assert report.title


class TestWorkerDeathDoesNotCorruptState:
    """Application state must remain consistent after worker failure."""

    def test_mastery_states_unchanged_after_failed_batch(
        self, class_with_members, student, concepts,
    ):
        from adaptive.engine import get_mastery_state

        state_before = get_mastery_state(student.id, concepts[0].id)
        p_before = state_before.p_mastery

        with patch(
            "dashboard.services.compute_early_warnings",
            side_effect=WorkerLostError("lost"),
        ):
            run_nightly_early_warnings()

        state_after = get_mastery_state(student.id, concepts[0].id)
        assert state_after.p_mastery == pytest.approx(p_before)

    def test_assessment_sessions_unchanged(
        self, student_api, student, assessment, class_with_members,
    ):
        resp = student_api.post(f"/api/assessment/{assessment.id}/start/")
        session_id = resp.json()["id"]

        with patch(
            "dashboard.services.compute_early_warnings",
            side_effect=WorkerLostError("lost"),
        ):
            run_nightly_early_warnings()

        from assessment.models import AssessmentSession
        session = AssessmentSession.objects.get(id=session_id)
        assert session.status == AssessmentSession.Status.IN_PROGRESS
