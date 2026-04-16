import pytest
from analytics.tasks import run_nightly_early_warnings, generate_weekly_report
from analytics.models import PilotReport

pytestmark = [pytest.mark.django_db, pytest.mark.recovery]


class TestNightlyTask:

    def test_runs_with_no_classes(self):
        result = run_nightly_early_warnings()
        assert result == 0

    def test_runs_with_class_no_students(self, student_class):
        result = run_nightly_early_warnings()
        assert result == 0

    def test_runs_with_populated_class(self, class_with_members):
        result = run_nightly_early_warnings()
        assert isinstance(result, int)


class TestWeeklyReportTask:

    def test_generates_report(self, class_with_members):
        report_id = generate_weekly_report(class_with_members.id, 1)
        assert PilotReport.objects.filter(id=report_id).exists()
        report = PilotReport.objects.get(id=report_id)
        assert report.week_number == 1
        assert report.kpi_data
