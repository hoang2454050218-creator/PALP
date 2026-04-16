import pytest
from datetime import timedelta
from django.utils import timezone

from accounts.models import User, StudentClass, ClassMembership, LecturerClassAssignment
from adaptive.models import MasteryState, TaskAttempt
from assessment.models import (
    Assessment, AssessmentQuestion, AssessmentSession, AssessmentResponse,
)
from curriculum.models import Course, Concept, Milestone, MicroTask, SupplementaryContent
from dashboard.models import Alert
from events.models import EventLog


@pytest.fixture
def populated_db(db):
    """
    Full database state suitable for backup/restore and recovery tests.
    Creates users, classes, curriculum, mastery states, assessment sessions,
    task attempts, alerts, and events.
    Returns a dict of all created objects for assertion after restore.
    """
    course = Course.objects.create(code="SBVL", name="Suc ben vat lieu")
    concepts = []
    for i, (code, name) in enumerate([
        ("NL", "Noi luc"), ("US", "Ung suat"), ("BD", "Bien dang"),
    ], start=1):
        concepts.append(
            Concept.objects.create(course=course, code=code, name=name, order=i)
        )

    m1 = Milestone.objects.create(course=course, title="M1", order=1, target_week=2)
    m1.concepts.add(concepts[0])

    tasks = []
    for i, concept in enumerate(concepts):
        tasks.append(MicroTask.objects.create(
            milestone=m1, concept=concept,
            title=f"Task {concept.code}", difficulty=1, estimated_minutes=5,
            content={"question": f"Q-{concept.code}?", "options": ["A", "B"], "correct_answer": "A"},
        ))

    SupplementaryContent.objects.create(
        concept=concepts[0], title="Extra NL", body="...",
        content_type=SupplementaryContent.ContentType.TEXT,
        difficulty_target=1, order=1,
    )

    assessment = Assessment.objects.create(course=course, title="Entry", time_limit_minutes=15)
    for i, c in enumerate(concepts):
        AssessmentQuestion.objects.create(
            assessment=assessment, concept=c,
            text=f"Q {c.name}?", options=["A", "B", "C"], correct_answer="A", order=i + 1,
        )

    student_class = StudentClass.objects.create(name="SBVL-01", academic_year="2025-2026")

    students = []
    for idx in range(1, 6):
        s = User.objects.create_user(
            username=f"sv_rec_{idx}", password="Str0ngP@ss!",
            role=User.Role.STUDENT, student_id=f"22KT{idx:04d}",
        )
        students.append(s)
        ClassMembership.objects.create(student=s, student_class=student_class)

    lecturer = User.objects.create_user(
        username="gv_rec", password="Str0ngP@ss!",
        role=User.Role.LECTURER,
    )
    LecturerClassAssignment.objects.create(
        lecturer=lecturer, student_class=student_class,
    )

    admin = User.objects.create_user(
        username="admin_rec", password="Str0ngP@ss!",
        role=User.Role.ADMIN,
    )

    mastery_states = []
    for s in students:
        for c in concepts:
            ms = MasteryState.objects.create(
                student=s, concept=c, p_mastery=0.4,
                attempt_count=3, correct_count=1,
            )
            mastery_states.append(ms)

    task_attempts = []
    for s in students[:3]:
        for t in tasks:
            ta = TaskAttempt.objects.create(
                student=s, task=t, score=80, is_correct=True,
                answer={"selected": "A"}, attempt_number=1, duration_seconds=60,
            )
            task_attempts.append(ta)

    session = AssessmentSession.objects.create(
        student=students[0], assessment=assessment,
        status=AssessmentSession.Status.IN_PROGRESS,
    )
    for q in assessment.questions.all():
        AssessmentResponse.objects.create(
            session=session, question=q,
            answer="A", is_correct=True, time_taken_seconds=30,
        )

    alerts = []
    now = timezone.now()
    for s in students[:2]:
        alert = Alert.objects.create(
            student=s, student_class=student_class,
            severity=Alert.Severity.RED,
            trigger_type=Alert.TriggerType.INACTIVITY,
            reason=f"{s.username} inactive",
            evidence={"days_inactive": 6},
            suggested_action="Contact student",
        )
        alerts.append(alert)

    return {
        "course": course,
        "concepts": concepts,
        "tasks": tasks,
        "students": students,
        "lecturer": lecturer,
        "admin": admin,
        "student_class": student_class,
        "mastery_states": mastery_states,
        "task_attempts": task_attempts,
        "assessment": assessment,
        "session": session,
        "alerts": alerts,
        "counts": {
            "users": User.objects.count(),
            "mastery_states": MasteryState.objects.count(),
            "task_attempts": TaskAttempt.objects.count(),
            "alerts": Alert.objects.count(),
            "assessment_sessions": AssessmentSession.objects.count(),
            "assessment_responses": AssessmentResponse.objects.count(),
        },
    }
