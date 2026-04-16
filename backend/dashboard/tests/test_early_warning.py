import pytest
from datetime import timedelta

from django.utils import timezone

from adaptive.models import TaskAttempt, StudentPathway
from dashboard.models import Alert
from dashboard.services import compute_early_warnings, get_class_overview
from events.models import EventLog

pytestmark = pytest.mark.django_db


def _create_session_event(student, days_ago=0, hours_ago=0):
    return EventLog.objects.create(
        user=student,
        event_name=EventLog.EventName.SESSION_STARTED,
        created_at=timezone.now() - timedelta(days=days_ago, hours=hours_ago),
    )


class TestInactivityAlert:

    def test_six_days_inactive_triggers_red(self, student, class_with_members):
        _create_session_event(student, days_ago=6)
        alerts = compute_early_warnings(class_with_members.id)
        student_alerts = [
            a for a in alerts
            if a.student == student and a.trigger_type == Alert.TriggerType.INACTIVITY
        ]
        assert len(student_alerts) == 1
        assert student_alerts[0].severity == Alert.Severity.RED

    def test_four_days_inactive_triggers_yellow(self, student, class_with_members):
        _create_session_event(student, days_ago=4)
        alerts = compute_early_warnings(class_with_members.id)
        student_alerts = [
            a for a in alerts
            if a.student == student and a.trigger_type == Alert.TriggerType.INACTIVITY
        ]
        assert len(student_alerts) == 1
        assert student_alerts[0].severity == Alert.Severity.YELLOW

    def test_recently_active_no_alert(self, student, class_with_members):
        _create_session_event(student, hours_ago=2)
        alerts = compute_early_warnings(class_with_members.id)
        student_alerts = [
            a for a in alerts
            if a.student == student and a.trigger_type == Alert.TriggerType.INACTIVITY
        ]
        assert len(student_alerts) == 0

    def test_no_duplicate_alerts(self, student, class_with_members):
        _create_session_event(student, days_ago=6)
        compute_early_warnings(class_with_members.id)
        count_first = Alert.objects.filter(
            student=student, trigger_type=Alert.TriggerType.INACTIVITY,
        ).count()
        compute_early_warnings(class_with_members.id)
        count_second = Alert.objects.filter(
            student=student, trigger_type=Alert.TriggerType.INACTIVITY,
        ).count()
        assert count_first == count_second


class TestRetryFailureAlert:

    def test_threshold_failures_triggers_red(self, student, class_with_members, micro_tasks):
        for _ in range(4):
            TaskAttempt.objects.create(
                student=student, task=micro_tasks[0], is_correct=False,
            )
        alerts = compute_early_warnings(class_with_members.id)
        retry_alerts = [
            a for a in alerts
            if a.student == student and a.trigger_type == Alert.TriggerType.RETRY_FAILURE
        ]
        assert len(retry_alerts) == 1
        assert retry_alerts[0].severity == Alert.Severity.RED


class TestMilestoneLagAlert:

    def test_low_completion_triggers_yellow(
        self, student, class_with_members, course, milestones,
    ):
        StudentPathway.objects.create(
            student=student, course=course,
            current_milestone=milestones[0], milestones_completed=[],
        )
        alerts = compute_early_warnings(class_with_members.id)
        lag_alerts = [
            a for a in alerts
            if a.student == student and a.trigger_type == Alert.TriggerType.MILESTONE_LAG
        ]
        assert len(lag_alerts) == 1
        assert lag_alerts[0].severity == Alert.Severity.YELLOW


class TestClassOverview:

    def test_returns_correct_counts(self, student, student_b, class_with_members):
        Alert.objects.create(
            student=student, student_class=class_with_members,
            severity=Alert.Severity.RED,
            trigger_type=Alert.TriggerType.INACTIVITY, reason="Inactive",
        )
        Alert.objects.create(
            student=student_b, student_class=class_with_members,
            severity=Alert.Severity.YELLOW,
            trigger_type=Alert.TriggerType.MILESTONE_LAG, reason="Slow",
        )
        overview = get_class_overview(class_with_members.id)
        assert overview["total_students"] == 2
        assert overview["needs_intervention"] == 1
        assert overview["needs_attention"] == 1
        assert overview["on_track"] == 0
