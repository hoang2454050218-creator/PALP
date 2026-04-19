"""
Goal-hierarchy + Daily-plan service layer.

The headline function is ``generate_daily_plan(student)`` which produces
1-3 actionable items for the North Star "Hôm nay làm gì" panel. The
ordering mirrors the SDT principles in
``docs/MOTIVATION_DESIGN.md``:

* low-mastery concept practice (Competence — recover the weakest concept)
* a milestone-progressing micro-task (Autonomy — choice toward the goal)
* an optional spaced-repetition / variety task (Relatedness — keep
  the learning experience alive without burning intrinsic motivation)

The plan is intentionally short — 1-3 items, never gamified, never
labelled "challenge of the day". A student can always opt out.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Iterable

from django.db.models import Count
from django.utils import timezone

from accounts.models import User

logger = logging.getLogger("palp")

DAILY_PLAN_MAX_ITEMS = 3


@dataclass
class DailyPlanItem:
    kind: str  # "weak_concept" | "milestone_task" | "variety_review"
    title: str
    rationale: str
    micro_task_id: int | None = None
    concept_id: int | None = None
    estimated_minutes: int | None = None


@dataclass
class DailyPlan:
    student_id: int
    date: date
    items: list[DailyPlanItem] = field(default_factory=list)
    weekly_goal_id: int | None = None


def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def get_active_weekly_goal(student: User, *, today: date | None = None):
    today = today or timezone.localdate()
    from .models import WeeklyGoal

    week_start = monday_of(today)
    return WeeklyGoal.objects.filter(student=student, week_start=week_start).first()


def get_active_semester_goals(student: User):
    from .models import SemesterGoal

    return SemesterGoal.objects.filter(student=student, is_active=True).select_related("course")


# ---------------------------------------------------------------------------
# Daily plan
# ---------------------------------------------------------------------------


def generate_daily_plan(student: User, *, today: date | None = None) -> DailyPlan:
    """Build the 1-3 item plan for the North Star panel.

    Pure read; no side effects. Frontend caches the response for the day
    and re-renders when the underlying mastery state changes.
    """
    today = today or timezone.localdate()
    weekly = get_active_weekly_goal(student, today=today)
    plan = DailyPlan(
        student_id=student.id,
        date=today,
        weekly_goal_id=weekly.id if weekly else None,
    )

    seen_task_ids: set[int] = set()

    weak_item = _suggest_weak_concept_task(student, seen=seen_task_ids)
    if weak_item:
        plan.items.append(weak_item)
        if weak_item.micro_task_id:
            seen_task_ids.add(weak_item.micro_task_id)

    milestone_item = _suggest_milestone_task(student, seen=seen_task_ids)
    if milestone_item:
        plan.items.append(milestone_item)
        if milestone_item.micro_task_id:
            seen_task_ids.add(milestone_item.micro_task_id)

    if len(plan.items) < DAILY_PLAN_MAX_ITEMS:
        variety = _suggest_variety_task(student, seen=seen_task_ids)
        if variety:
            plan.items.append(variety)

    return plan


def _suggest_weak_concept_task(student: User, *, seen: set[int]) -> DailyPlanItem | None:
    """Recommend a low-difficulty practice on the lowest-mastery concept."""
    from adaptive.models import MasteryState
    from curriculum.models import MicroTask

    weak = (
        MasteryState.objects.filter(student=student)
        .order_by("p_mastery")
        .select_related("concept")
        .first()
    )
    if not weak:
        return None
    if weak.p_mastery >= 0.85:
        return None  # student is doing well — no remediation needed

    task = (
        MicroTask.objects
        .filter(concept=weak.concept, is_active=True)
        .exclude(id__in=seen)
        .order_by("difficulty", "id")
        .first()
    )
    if not task:
        return None

    return DailyPlanItem(
        kind="weak_concept",
        title=f"Củng cố: {weak.concept.name}",
        rationale=(
            f"Mức nắm vững hiện tại {weak.p_mastery:.0%} — bài tập ngắn này "
            f"giúp bạn ổn định trước khi đi tiếp."
        ),
        micro_task_id=task.id,
        concept_id=weak.concept.id,
        estimated_minutes=getattr(task, "estimated_minutes", None) or 10,
    )


def _suggest_milestone_task(student: User, *, seen: set[int]) -> DailyPlanItem | None:
    """Recommend the next task toward the current pathway milestone."""
    from adaptive.models import StudentPathway
    from curriculum.models import MicroTask

    pathway = (
        StudentPathway.objects
        .filter(student=student, is_active=True)
        .select_related("current_concept", "current_milestone")
        .first()
    )
    if not pathway or not pathway.current_milestone:
        return None

    task_qs = MicroTask.objects.filter(
        milestone=pathway.current_milestone, is_active=True,
    ).exclude(id__in=seen)
    if pathway.current_concept_id:
        task_qs = task_qs.filter(concept=pathway.current_concept)
    task = task_qs.order_by("difficulty", "id").first()
    if not task:
        return None

    return DailyPlanItem(
        kind="milestone_task",
        title=f"Tiến tới: {pathway.current_milestone.title}",
        rationale=(
            "Bước tiếp theo trên lộ trình của bạn. Hoàn thành đều đặn hơn "
            "là tốt hơn hoàn thành dồn cuối tuần."
        ),
        micro_task_id=task.id,
        concept_id=pathway.current_concept_id,
        estimated_minutes=getattr(task, "estimated_minutes", None) or 12,
    )


def _suggest_variety_task(student: User, *, seen: set[int]) -> DailyPlanItem | None:
    """Optional review task on a *different* concept than the prior items."""
    from adaptive.models import MasteryState
    from curriculum.models import MicroTask

    seen_concept_ids = set(
        MicroTask.objects.filter(id__in=seen).values_list("concept_id", flat=True)
    )

    candidates = (
        MasteryState.objects.filter(student=student, p_mastery__gte=0.4, p_mastery__lt=0.85)
        .exclude(concept_id__in=seen_concept_ids)
        .order_by("-last_updated")[:5]
    )
    for state in candidates:
        task = (
            MicroTask.objects
            .filter(concept=state.concept, is_active=True)
            .exclude(id__in=seen)
            .order_by("difficulty", "id")
            .first()
        )
        if task:
            return DailyPlanItem(
                kind="variety_review",
                title=f"Ôn lại: {state.concept.name}",
                rationale=(
                    "Quay lại concept đã học để giữ retention dài hạn — "
                    "gợi ý từ nguyên lý spaced practice."
                ),
                micro_task_id=task.id,
                concept_id=state.concept.id,
                estimated_minutes=getattr(task, "estimated_minutes", None) or 8,
            )
    return None


# ---------------------------------------------------------------------------
# Goal helpers
# ---------------------------------------------------------------------------


def upsert_weekly_goal(
    *,
    student: User,
    week_start: date,
    target_minutes: int,
    target_concept_ids: list[int] | None = None,
    target_micro_task_count: int = 10,
    semester_goal=None,
):
    from .models import WeeklyGoal

    obj, created = WeeklyGoal.objects.update_or_create(
        student=student,
        week_start=week_start,
        defaults={
            "target_minutes": target_minutes,
            "target_concept_ids": target_concept_ids or [],
            "target_micro_task_count": target_micro_task_count,
            "semester_goal": semester_goal,
        },
    )
    if created:
        obj.status = WeeklyGoal.Status.PLANNED
        obj.save(update_fields=["status"])
    if created:
        # Emit goal_set event (best-effort — never block on it)
        try:
            from events.emitter import emit_event
            from events.models import EventLog

            emit_event(
                EventLog.EventName.GOAL_SET,
                actor=student,
                actor_type=EventLog.ActorType.STUDENT,
                properties={
                    "goal_type": "weekly",
                    "goal_id": obj.id,
                    "target_minutes": obj.target_minutes,
                    "target_concepts": obj.target_concept_ids,
                },
            )
        except Exception:
            logger.exception("Failed to emit goal_set for weekly_goal=%s", obj.id)
    return obj
