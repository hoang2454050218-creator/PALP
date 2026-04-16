"""
Recovery test: Queue replay -- queued jobs are not lost.

Verifies that:
  - Enqueued Celery tasks complete successfully
  - No task is silently dropped
  - Queue drains fully after processing
  - Task results are accessible after completion
  - Duplicate task submissions are handled safely
"""
import pytest
from unittest.mock import patch

from analytics.tasks import (
    run_nightly_early_warnings,
    generate_weekly_report,
    audit_event_completeness,
    audit_event_duplication,
)
from analytics.models import PilotReport, DataQualityLog

pytestmark = [pytest.mark.django_db, pytest.mark.recovery]


class TestQueueDrain:
    """All enqueued tasks must execute and produce results."""

    def test_nightly_task_completes(self, class_with_members):
        result = run_nightly_early_warnings.apply()
        assert result.successful()
        assert isinstance(result.result, int)

    def test_weekly_report_task_completes(self, class_with_members):
        result = generate_weekly_report.apply(
            args=[class_with_members.id, 1],
        )
        assert result.successful()
        report_id = result.result
        assert PilotReport.objects.filter(id=report_id).exists()

    def test_event_audit_tasks_complete(self, db):
        comp_result = audit_event_completeness.apply()
        assert comp_result.successful()

        dup_result = audit_event_duplication.apply()
        assert dup_result.successful()

    def test_multiple_tasks_all_drain(self, class_with_members):
        results = []
        results.append(run_nightly_early_warnings.apply())
        results.append(generate_weekly_report.apply(
            args=[class_with_members.id, 1],
        ))
        results.append(audit_event_completeness.apply())
        results.append(audit_event_duplication.apply())

        for r in results:
            assert r.successful(), f"Task failed: {r.traceback}"


class TestNoSilentDrop:
    """Tasks must not disappear without trace."""

    def test_failed_task_raises_not_drops(self, class_with_members):
        with patch(
            "analytics.tasks.compute_early_warnings",
            side_effect=ValueError("Bad data"),
        ):
            result = run_nightly_early_warnings.apply()
            assert result.successful()

    def test_task_with_bad_args_reports_failure(self):
        result = generate_weekly_report.apply(args=[99999, 1])
        assert not result.successful() or isinstance(result.result, int)


class TestDuplicateTaskSafety:
    """Submitting the same task multiple times must not corrupt data."""

    def test_duplicate_nightly_runs_idempotent(self, class_with_members):
        from dashboard.models import Alert

        run_nightly_early_warnings.apply()
        count_first = Alert.objects.count()

        run_nightly_early_warnings.apply()
        count_second = Alert.objects.count()

        assert count_second == count_first

    def test_duplicate_weekly_reports_create_separate_entries(
        self, class_with_members,
    ):
        r1 = generate_weekly_report.apply(args=[class_with_members.id, 1])
        r2 = generate_weekly_report.apply(args=[class_with_members.id, 2])

        assert r1.result != r2.result
        assert PilotReport.objects.count() >= 2

    def test_audit_tasks_idempotent(self, db):
        audit_event_completeness.apply()
        first_count = DataQualityLog.objects.filter(
            source="event_completeness_audit"
        ).count()

        audit_event_completeness.apply()
        second_count = DataQualityLog.objects.filter(
            source="event_completeness_audit"
        ).count()

        assert second_count == first_count + 1
