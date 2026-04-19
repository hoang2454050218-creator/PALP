from datetime import date, datetime, time, timedelta, timezone as tz

import pytest
from django.utils import timezone

from goals.drift_detector import (
    detect_drift_for_active_goals,
    evaluate_weekly_goal,
    measure_actual_focus_minutes,
)
from goals.models import WeeklyGoal
from goals.services import monday_of
from signals.models import SignalSession

pytestmark = pytest.mark.django_db


@pytest.fixture
def weekly(student):
    return WeeklyGoal.objects.create(
        student=student,
        week_start=monday_of(timezone.localdate()),
        target_minutes=300,
        target_micro_task_count=10,
    )


def _signal_session(student, week_start, focus_minutes, raw_session_id="rs-1"):
    start_dt = timezone.make_aware(datetime.combine(week_start, time(9, 0)))
    return SignalSession.objects.create(
        student=student,
        raw_session_id=raw_session_id,
        window_start=start_dt,
        window_end=start_dt + timedelta(minutes=5),
        focus_minutes=focus_minutes,
        idle_minutes=0,
    )


class TestMeasureFocus:
    def test_zero_when_no_signals(self, student):
        assert measure_actual_focus_minutes(student, week_start=date(2026, 4, 13)) == 0.0

    def test_sums_within_week(self, student):
        week = monday_of(timezone.localdate())
        _signal_session(student, week, 30, raw_session_id="r1")
        _signal_session(student, week, 45, raw_session_id="r2")
        assert measure_actual_focus_minutes(student, week_start=week) == 75.0

    def test_excludes_other_weeks(self, student):
        week = monday_of(timezone.localdate())
        _signal_session(student, week, 60)
        _signal_session(student, week - timedelta(days=14), 999, raw_session_id="other")
        assert measure_actual_focus_minutes(student, week_start=week) == 60.0


class TestEvaluateWeeklyGoal:
    def test_no_drift_when_target_met(self, student, weekly):
        _signal_session(student, weekly.week_start, 320)
        result = evaluate_weekly_goal(weekly)
        assert result.drifted is False
        assert result.drift_pct == 0.0

    def test_drift_above_threshold(self, student, weekly):
        # target 300, actual 100 -> drift = 200/300 = 0.667
        _signal_session(student, weekly.week_start, 100)
        result = evaluate_weekly_goal(weekly)
        assert result.drifted is True
        assert result.drift_pct > 0.5
        weekly.refresh_from_db()
        assert weekly.status == WeeklyGoal.Status.DRIFTED

    def test_event_emitted_on_first_cross(self, student, weekly):
        # First check: drift -> event emitted
        _signal_session(student, weekly.week_start, 100, raw_session_id="r1")
        first = evaluate_weekly_goal(weekly)
        assert first.event_emitted is True

        # Second check (same drift level): should NOT re-emit
        second = evaluate_weekly_goal(weekly)
        assert second.event_emitted is False

    def test_recovers_to_in_progress_when_back_under_threshold(self, student, weekly):
        _signal_session(student, weekly.week_start, 100, raw_session_id="r1")
        evaluate_weekly_goal(weekly)
        # Add a lot more focus
        _signal_session(student, weekly.week_start, 250, raw_session_id="r2")
        result = evaluate_weekly_goal(weekly)
        assert result.drifted is False
        weekly.refresh_from_db()
        assert weekly.status == WeeklyGoal.Status.IN_PROGRESS


class TestDetectDriftForActiveGoals:
    def test_runs_only_for_current_week(self, student, weekly):
        # Old goal from prior week should be ignored
        WeeklyGoal.objects.create(
            student=student,
            week_start=weekly.week_start - timedelta(days=14),
            target_minutes=300,
        )
        _signal_session(student, weekly.week_start, 50)
        results = detect_drift_for_active_goals()
        assert len(results) == 1
        assert results[0].weekly_goal_id == weekly.id

    def test_skips_completed_or_abandoned(self, student, weekly):
        weekly.status = WeeklyGoal.Status.COMPLETED
        weekly.save()
        _signal_session(student, weekly.week_start, 0)
        results = detect_drift_for_active_goals()
        assert results == []
