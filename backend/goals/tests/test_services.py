from datetime import date, timedelta

import pytest

from adaptive.models import MasteryState, StudentPathway
from goals.services import (
    DAILY_PLAN_MAX_ITEMS,
    generate_daily_plan,
    monday_of,
    upsert_weekly_goal,
)
from goals.models import WeeklyGoal

pytestmark = pytest.mark.django_db


class TestMondayOf:
    def test_returns_monday_for_any_weekday(self):
        # 2026-04-15 is a Wednesday -> previous Monday is 2026-04-13
        assert monday_of(date(2026, 4, 15)) == date(2026, 4, 13)

    def test_idempotent_on_monday(self):
        monday = date(2026, 4, 13)
        assert monday_of(monday) == monday


class TestUpsertWeeklyGoal:
    def test_creates(self, student):
        wg = upsert_weekly_goal(
            student=student,
            week_start=date(2026, 4, 13),
            target_minutes=300,
            target_micro_task_count=10,
        )
        assert wg.pk is not None
        assert wg.target_minutes == 300

    def test_idempotent_for_same_week(self, student):
        a = upsert_weekly_goal(student=student, week_start=date(2026, 4, 13), target_minutes=300)
        b = upsert_weekly_goal(student=student, week_start=date(2026, 4, 13), target_minutes=400)
        assert a.pk == b.pk
        b.refresh_from_db()
        assert b.target_minutes == 400


class TestGenerateDailyPlan:
    def test_empty_for_brand_new_student(self, student, course):
        plan = generate_daily_plan(student)
        assert plan.student_id == student.id
        assert plan.items == []

    def test_recommends_weak_concept_when_mastery_low(
        self, student, course, concepts, micro_tasks
    ):
        weak = concepts[0]
        MasteryState.objects.create(student=student, concept=weak, p_mastery=0.2)
        plan = generate_daily_plan(student)
        assert plan.items, "expected at least one suggestion"
        kinds = [it.kind for it in plan.items]
        assert "weak_concept" in kinds
        weak_item = next(it for it in plan.items if it.kind == "weak_concept")
        assert weak_item.concept_id == weak.id

    def test_skips_weak_when_mastery_already_solid(self, student, course, concepts, micro_tasks):
        for c in concepts:
            MasteryState.objects.create(student=student, concept=c, p_mastery=0.92)
        plan = generate_daily_plan(student)
        kinds = [it.kind for it in plan.items]
        assert "weak_concept" not in kinds

    def test_recommends_milestone_task_when_pathway_active(
        self, student, course, concepts, milestones, micro_tasks
    ):
        StudentPathway.objects.create(
            student=student, course=course,
            current_concept=concepts[0],
            current_milestone=milestones[0],
        )
        plan = generate_daily_plan(student)
        kinds = [it.kind for it in plan.items]
        assert "milestone_task" in kinds

    def test_caps_at_max_items(
        self, student, course, concepts, milestones, micro_tasks
    ):
        for c in concepts:
            MasteryState.objects.create(student=student, concept=c, p_mastery=0.5)
        StudentPathway.objects.create(
            student=student, course=course,
            current_concept=concepts[0],
            current_milestone=milestones[0],
        )
        plan = generate_daily_plan(student)
        assert len(plan.items) <= DAILY_PLAN_MAX_ITEMS

    def test_no_duplicate_micro_tasks(self, student, course, concepts, milestones, micro_tasks):
        for c in concepts:
            MasteryState.objects.create(student=student, concept=c, p_mastery=0.5)
        StudentPathway.objects.create(
            student=student, course=course,
            current_concept=concepts[0],
            current_milestone=milestones[0],
        )
        plan = generate_daily_plan(student)
        task_ids = [it.micro_task_id for it in plan.items if it.micro_task_id is not None]
        assert len(task_ids) == len(set(task_ids))
