from datetime import date

import pytest
from django.utils import timezone

from goals.models import (
    EffortRating,
    GoalReflection,
    StrategyEffectiveness,
    StrategyPlan,
    WeeklyGoal,
)
from goals.reflection import (
    ReflectionSubmission,
    open_reflections_for_week,
    submit_reflection,
)
from goals.services import monday_of

pytestmark = pytest.mark.django_db


@pytest.fixture
def weekly(student):
    return WeeklyGoal.objects.create(
        student=student,
        week_start=monday_of(timezone.localdate()),
        target_minutes=300,
    )


@pytest.fixture
def strategy(weekly):
    return StrategyPlan.objects.create(
        weekly_goal=weekly,
        strategy=StrategyPlan.Strategy.SPACED_PRACTICE,
        predicted_minutes=120,
    )


class TestSubmitReflection:
    def test_creates_reflection_row(self, student, weekly):
        obj = submit_reflection(
            student=student,
            payload=ReflectionSubmission(
                weekly_goal_id=weekly.id,
                learned_text="Tôi đã hiểu nội lực",
                struggle_text="Tích phân biểu đồ",
                next_priority_text="Ôn lại ứng suất",
            ),
        )
        assert obj.pk is not None
        assert obj.submitted_at is not None
        assert GoalReflection.objects.filter(weekly_goal=weekly).count() == 1

    def test_idempotent_overwrites(self, student, weekly):
        submit_reflection(
            student=student,
            payload=ReflectionSubmission(weekly_goal_id=weekly.id, learned_text="first"),
        )
        submit_reflection(
            student=student,
            payload=ReflectionSubmission(weekly_goal_id=weekly.id, learned_text="second"),
        )
        assert GoalReflection.objects.filter(weekly_goal=weekly).count() == 1
        assert GoalReflection.objects.get(weekly_goal=weekly).learned_text == "second"

    def test_persists_effort_rating(self, student, weekly):
        submit_reflection(
            student=student,
            payload=ReflectionSubmission(
                weekly_goal_id=weekly.id,
                effort_rating=4,
                effort_note="thấy hiệu quả",
            ),
        )
        rating = EffortRating.objects.get(weekly_goal=weekly)
        assert rating.rating == 4

    def test_rejects_out_of_range_effort(self, student, weekly):
        with pytest.raises(ValueError, match="effort_rating"):
            submit_reflection(
                student=student,
                payload=ReflectionSubmission(weekly_goal_id=weekly.id, effort_rating=6),
            )

    def test_persists_strategy_effectiveness(self, student, weekly, strategy):
        submit_reflection(
            student=student,
            payload=ReflectionSubmission(
                weekly_goal_id=weekly.id,
                strategy_effectiveness={
                    strategy.id: {"rating": 5, "will_repeat": True, "note": "rất tốt"},
                },
            ),
        )
        eff = StrategyEffectiveness.objects.get(strategy_plan=strategy)
        assert eff.rating == 5 and eff.will_repeat is True

    def test_ignores_unknown_strategy_id(self, student, weekly):
        submit_reflection(
            student=student,
            payload=ReflectionSubmission(
                weekly_goal_id=weekly.id,
                strategy_effectiveness={9999: {"rating": 3}},
            ),
        )
        assert StrategyEffectiveness.objects.count() == 0


class TestOpenReflectionsForWeek:
    def test_creates_stubs_idempotently(self, student, weekly):
        open_reflections_for_week(week_start=weekly.week_start)
        open_reflections_for_week(week_start=weekly.week_start)  # second call no-ops
        assert GoalReflection.objects.filter(weekly_goal=weekly).count() == 1

    def test_returns_count_of_new_stubs(self, student, weekly):
        n = open_reflections_for_week(week_start=weekly.week_start)
        assert n == 1
        n2 = open_reflections_for_week(week_start=weekly.week_start)
        assert n2 == 0
