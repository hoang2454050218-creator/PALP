import pytest

from analytics.models import PilotReport
from analytics.tasks import run_nightly_early_warnings, generate_weekly_report

pytestmark = pytest.mark.django_db


class TestRunNightlyEarlyWarnings:
    def test_runs_for_all_classes_returns_count(self, class_with_members):
        result = run_nightly_early_warnings()
        assert isinstance(result, int)

    def test_returns_zero_when_no_alerts_needed(self, student_class):
        result = run_nightly_early_warnings()
        assert result == 0


class TestGenerateWeeklyReport:
    def test_single_class_returns_report_id(self, class_with_members):
        result = generate_weekly_report(
            class_id=class_with_members.id, week_number=1,
        )

        assert isinstance(result, int)
        assert PilotReport.objects.filter(id=result).exists()

    def test_all_classes_returns_id_list(self, class_with_members):
        result = generate_weekly_report(class_id=None, week_number=1)

        assert isinstance(result, list)
        assert len(result) >= 1
        for report_id in result:
            assert PilotReport.objects.filter(id=report_id).exists()
