"""
One-shot seeder for the North Star browser demo.

Creates (or refreshes) a student account with realistic data so the
North Star page renders with real content instead of empty states.

Usage (from inside the backend container):

    python manage.py shell < seed_north_star_demo.py
"""
import os
from datetime import timedelta

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "palp.settings.development")
django.setup()

from django.utils import timezone

from accounts.models import ClassMembership, LecturerClassAssignment, StudentClass, User
from adaptive.models import MasteryState, StudentPathway
from curriculum.models import Concept, Course, MicroTask, Milestone
from goals.models import (
    CareerGoal, SemesterGoal, WeeklyGoal, StrategyPlan,
)
from goals.services import monday_of
from privacy.models import ConsentRecord
from signals.models import SignalSession

USERNAME = "demo_student"
PASSWORD = "Str0ngP@ss!"
LECTURER_USERNAME = "demo_lecturer"


def upsert_users():
    student, created = User.objects.get_or_create(
        username=USERNAME,
        defaults={
            "role": User.Role.STUDENT,
            "first_name": "Nguyễn",
            "last_name": "Văn Demo",
            "email": "demo@palp.local",
            "student_id": "DEMO0001",
        },
    )
    student.set_password(PASSWORD)
    student.is_active = True
    student.save()

    lecturer, _ = User.objects.get_or_create(
        username=LECTURER_USERNAME,
        defaults={
            "role": User.Role.LECTURER,
            "first_name": "Lê",
            "last_name": "Thị Cố Vấn",
            "email": "demo_lecturer@palp.local",
        },
    )
    lecturer.set_password(PASSWORD)
    lecturer.is_active = True
    lecturer.save()
    return student, lecturer


def upsert_class(student, lecturer):
    klass, _ = StudentClass.objects.get_or_create(
        name="DEMO-2026", defaults={"academic_year": "2026-2027"},
    )
    ClassMembership.objects.get_or_create(student=student, student_class=klass)
    LecturerClassAssignment.objects.get_or_create(lecturer=lecturer, student_class=klass)
    return klass


def upsert_curriculum():
    course, _ = Course.objects.get_or_create(
        code="SBVL-DEMO",
        defaults={"name": "Sức bền vật liệu (demo)", "credits": 3, "is_active": True},
    )
    concept_specs = [
        ("NL", "Nội lực"),
        ("US", "Ứng suất"),
        ("BD", "Biến dạng"),
        ("UN", "Uốn"),
    ]
    concepts = []
    for order, (code, name) in enumerate(concept_specs, start=1):
        c, _ = Concept.objects.get_or_create(
            course=course, code=code,
            defaults={"name": name, "order": order, "is_active": True},
        )
        # Refresh order/name in case of pre-existing
        c.order = order
        c.name = name
        c.is_active = True
        c.save()
        concepts.append(c)

    milestone_specs = [
        ("M1: Cơ bản", 2, [concepts[0], concepts[1]]),
        ("M2: Nâng cao", 4, [concepts[2], concepts[3]]),
    ]
    milestones = []
    for order, (title, target_week, mc) in enumerate(milestone_specs, start=1):
        m, _ = Milestone.objects.get_or_create(
            course=course, title=title,
            defaults={"order": order, "target_week": target_week},
        )
        m.order = order
        m.target_week = target_week
        m.save()
        m.concepts.set(mc)
        milestones.append(m)

    micro_tasks = []
    for ms_idx, milestone in enumerate(milestones):
        for c in milestone.concepts.all():
            for difficulty in (1, 2):
                slug = f"{c.code}-{difficulty}"
                t, _ = MicroTask.objects.get_or_create(
                    milestone=milestone, concept=c, title=f"Bài {c.name} mức {difficulty}",
                    defaults={
                        "difficulty": difficulty,
                        "estimated_minutes": 6 + difficulty * 4,
                        "is_active": True,
                        "content": {
                            "question": f"Tính {c.name.lower()} mức {difficulty}?",
                            "options": ["A", "B", "C", "D"],
                            "correct_answer": "A",
                        },
                    },
                )
                t.is_active = True
                t.save(update_fields=["is_active"])
                micro_tasks.append(t)
    return course, concepts, milestones, micro_tasks


def upsert_consents(student):
    purposes = [
        "academic", "behavioral", "inference",
        "behavioral_signals", "cognitive_calibration",
    ]
    for p in purposes:
        ConsentRecord.objects.create(
            user=student, purpose=p, granted=True, version="1.1",
        )
    student.consent_given = True
    student.consent_given_at = timezone.now()
    student.save(update_fields=["consent_given", "consent_given_at"])


def seed_mastery(student, course, concepts):
    targets = [
        (concepts[0], 0.20),  # weak
        (concepts[1], 0.55),
        (concepts[2], 0.78),
        (concepts[3], 0.92),
    ]
    for c, p in targets:
        ms, _ = MasteryState.objects.get_or_create(student=student, concept=c)
        ms.p_mastery = p
        ms.attempt_count = max(ms.attempt_count, 6)
        ms.correct_count = int(ms.attempt_count * max(0.5, p))
        ms.save()


def seed_pathway(student, course, concepts, milestones):
    pathway, _ = StudentPathway.objects.get_or_create(
        student=student, course=course,
        defaults={
            "current_concept": concepts[1],
            "current_milestone": milestones[0],
            "current_difficulty": 2,
            "milestones_completed": [],
            "concepts_completed": [],
            "is_active": True,
        },
    )
    pathway.current_concept = concepts[1]
    pathway.current_milestone = milestones[0]
    pathway.is_active = True
    pathway.save()


def seed_goals(student, course):
    CareerGoal.objects.update_or_create(
        student=student,
        defaults={
            "label": "Backend developer (Python / Django)",
            "category": CareerGoal.Category.SOFTWARE_BACKEND,
            "horizon_months": 12,
            "notes": "Muốn đi chuyên sâu về performance + system design.",
        },
    )
    sg, _ = SemesterGoal.objects.update_or_create(
        student=student, course=course, semester="2026S2",
        defaults={
            "mastery_target": 0.75,
            "completion_target_pct": 80,
            "intent": "Học SBVL không phải để qua môn — cần làm nền cho Cơ học.",
            "started_at": timezone.localdate(),
            "is_active": True,
        },
    )
    week_start = monday_of(timezone.localdate())
    wg, _ = WeeklyGoal.objects.update_or_create(
        student=student, week_start=week_start,
        defaults={
            "semester_goal": sg,
            "target_minutes": 300,
            "target_micro_task_count": 8,
            "target_concept_ids": [],
            "status": WeeklyGoal.Status.IN_PROGRESS,
        },
    )
    StrategyPlan.objects.update_or_create(
        weekly_goal=wg, strategy=StrategyPlan.Strategy.SPACED_PRACTICE,
        defaults={
            "predicted_minutes": 180,
            "rationale": "Thử dãn cách thay vì học dồn cuối tuần như học kỳ trước.",
        },
    )
    return wg


def seed_signal_sessions(student, week_start):
    """Seed 100 minutes of focus + a frustration peak so drift > 40%."""
    SignalSession.objects.filter(
        student=student, window_start__date__gte=week_start,
    ).delete()
    base = timezone.make_aware(
        timezone.datetime.combine(week_start, timezone.datetime.min.time())
    ).replace(hour=9)
    for i in range(20):
        SignalSession.objects.create(
            student=student,
            raw_session_id=f"demo-rs-{i}",
            window_start=base + timedelta(minutes=i * 5),
            window_end=base + timedelta(minutes=i * 5 + 5),
            focus_minutes=4.0 if i < 10 else 2.5,
            idle_minutes=1.0 if i < 10 else 2.5,
            tab_switches=i % 3,
            hint_count=i % 2,
            frustration_score=0.6 if i in (8, 14) else 0.1,
            give_up_count=1 if i == 14 else 0,
            raw_event_count=10 + i,
        )


def main():
    student, lecturer = upsert_users()
    upsert_class(student, lecturer)
    course, concepts, milestones, _tasks = upsert_curriculum()
    upsert_consents(student)
    seed_mastery(student, course, concepts)
    seed_pathway(student, course, concepts, milestones)
    weekly = seed_goals(student, course)
    seed_signal_sessions(student, weekly.week_start)

    print("=" * 60)
    print(f"Seed complete. Login as: {USERNAME} / {PASSWORD}")
    print(f"Lecturer:                {LECTURER_USERNAME} / {PASSWORD}")
    print(f"Course: {course.code}")
    print(f"Weekly goal: target={weekly.target_minutes}m week_start={weekly.week_start}")
    print("=" * 60)


main()
