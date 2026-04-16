import pytest

from adaptive.models import MasteryState
from analytics.models import PilotReport
from analytics.services import generate_kpi_snapshot, generate_pilot_report

pytestmark = pytest.mark.django_db


class TestGenerateKPISnapshot:
    def test_returns_correct_structure(self, class_with_members):
        kpi = generate_kpi_snapshot(class_with_members.id, week_number=1)

        assert kpi["week"] == 1
        assert kpi["cohort_size"] == 2
        assert "timestamp" in kpi
        assert "active_learning_minutes_per_week" in kpi
        assert "micro_task_completion_rate" in kpi
        assert "dashboard_usage_per_week" in kpi
        assert "wellbeing" in kpi
        assert "mastery" in kpi
        assert "alerts" in kpi

    def test_completion_rate_zero_with_no_attempts(self, class_with_members):
        kpi = generate_kpi_snapshot(class_with_members.id, week_number=1)
        assert kpi["micro_task_completion_rate"] == 0

    def test_mastery_stats_computed(
        self, student, class_with_members, concepts
    ):
        MasteryState.objects.create(
            student=student,
            concept=concepts[0],
            p_mastery=0.75,
            attempt_count=10,
            correct_count=7,
        )

        kpi = generate_kpi_snapshot(class_with_members.id, week_number=1)

        assert kpi["mastery"]["avg_mastery"] > 0
        assert kpi["mastery"]["total_records"] >= 1

    def test_empty_class_handles_gracefully(self, student_class):
        kpi = generate_kpi_snapshot(student_class.id, week_number=1)

        assert kpi["cohort_size"] == 0
        assert kpi["active_learning_minutes_per_week"] == 0
        assert kpi["micro_task_completion_rate"] == 0


class TestGeneratePilotReport:
    def test_creates_report_with_correct_data(self, class_with_members):
        report = generate_pilot_report(class_with_members.id, week_number=1)

        assert report.pk is not None
        assert report.report_type == PilotReport.ReportType.WEEKLY
        assert report.week_number == 1
        assert report.title == "Báo cáo tuần 1"
        assert PilotReport.objects.filter(id=report.id).exists()

    def test_kpi_and_usage_data_populated(self, class_with_members):
        report = generate_pilot_report(class_with_members.id, week_number=2)

        assert isinstance(report.kpi_data, dict)
        assert "week" in report.kpi_data
        assert report.kpi_data["week"] == 2

        assert isinstance(report.usage_data, dict)
        assert "active_learning" in report.usage_data
        assert "completion" in report.usage_data
        assert "dashboard_usage" in report.usage_data
