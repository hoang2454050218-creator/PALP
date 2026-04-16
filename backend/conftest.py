import pytest
from rest_framework.test import APIClient

from accounts.models import User, StudentClass, ClassMembership, LecturerClassAssignment
from curriculum.models import (
    Course, Concept, ConceptPrerequisite, Milestone, MicroTask, SupplementaryContent,
)
from assessment.models import Assessment, AssessmentQuestion
from adaptive.models import MasteryState, StudentPathway
from events.models import EventLog


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@pytest.fixture
def student(db):
    return User.objects.create_user(
        username="test_student", password="Str0ngP@ss!",
        role=User.Role.STUDENT, student_id="22KT0001",
        first_name="Nguyen", last_name="Van A",
    )


@pytest.fixture
def student_b(db):
    return User.objects.create_user(
        username="test_student_b", password="Str0ngP@ss!",
        role=User.Role.STUDENT, student_id="22KT0002",
        first_name="Tran", last_name="Van B",
    )


@pytest.fixture
def lecturer(db):
    return User.objects.create_user(
        username="test_lecturer", password="Str0ngP@ss!",
        role=User.Role.LECTURER,
        first_name="Le", last_name="Thi C",
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="test_admin", password="Str0ngP@ss!",
        role=User.Role.ADMIN,
        first_name="Admin", last_name="User",
    )


# ---------------------------------------------------------------------------
# Class setup
# ---------------------------------------------------------------------------

@pytest.fixture
def student_class(db):
    return StudentClass.objects.create(name="SBVL-01", academic_year="2025-2026")


@pytest.fixture
def class_with_members(student, student_b, lecturer, student_class):
    ClassMembership.objects.create(student=student, student_class=student_class)
    ClassMembership.objects.create(student=student_b, student_class=student_class)
    LecturerClassAssignment.objects.create(lecturer=lecturer, student_class=student_class)
    return student_class


# ---------------------------------------------------------------------------
# Curriculum
# ---------------------------------------------------------------------------

@pytest.fixture
def course(db):
    return Course.objects.create(code="SBVL", name="Suc ben vat lieu")


@pytest.fixture
def concepts(course):
    c1 = Concept.objects.create(course=course, code="NL", name="Noi luc", order=1)
    c2 = Concept.objects.create(course=course, code="US", name="Ung suat", order=2)
    c3 = Concept.objects.create(course=course, code="BD", name="Bien dang", order=3)
    ConceptPrerequisite.objects.create(concept=c2, prerequisite=c1)
    ConceptPrerequisite.objects.create(concept=c3, prerequisite=c2)
    return [c1, c2, c3]


@pytest.fixture
def milestones(course, concepts):
    m1 = Milestone.objects.create(course=course, title="M1: Co ban", order=1, target_week=2)
    m2 = Milestone.objects.create(course=course, title="M2: Nang cao", order=2, target_week=4)
    m1.concepts.add(concepts[0])
    m2.concepts.add(concepts[1], concepts[2])
    return [m1, m2]


@pytest.fixture
def micro_tasks(milestones, concepts):
    t1 = MicroTask.objects.create(
        milestone=milestones[0], concept=concepts[0],
        title="Bai tap noi luc 1", difficulty=1, estimated_minutes=5,
        content={"question": "Noi luc tai mat cat A?", "options": ["10kN", "20kN", "30kN"], "correct_answer": "20kN"},
    )
    t2 = MicroTask.objects.create(
        milestone=milestones[0], concept=concepts[0],
        title="Bai tap noi luc 2", difficulty=2, estimated_minutes=8,
        content={"question": "Bieu do noi luc?", "options": ["A", "B", "C"], "correct_answer": "B"},
    )
    t3 = MicroTask.objects.create(
        milestone=milestones[1], concept=concepts[1],
        title="Bai tap ung suat", difficulty=2, estimated_minutes=10,
        content={"question": "Ung suat phap?", "options": ["sigma", "tau", "gamma"], "correct_answer": "sigma"},
    )
    return [t1, t2, t3]


@pytest.fixture
def supplementary(concepts):
    return SupplementaryContent.objects.create(
        concept=concepts[0], title="Giai thich noi luc",
        content_type=SupplementaryContent.ContentType.TEXT,
        body="Noi luc la luc ben trong...", difficulty_target=1, order=1,
    )


# ---------------------------------------------------------------------------
# Assessment
# ---------------------------------------------------------------------------

@pytest.fixture
def assessment(course, concepts):
    a = Assessment.objects.create(course=course, title="Entry Assessment", time_limit_minutes=15)
    for i, concept in enumerate(concepts):
        AssessmentQuestion.objects.create(
            assessment=a, concept=concept,
            text=f"Cau hoi ve {concept.name}?",
            options=["A", "B", "C", "D"], correct_answer="A", order=i + 1,
        )
    return a


# ---------------------------------------------------------------------------
# API clients
# ---------------------------------------------------------------------------

@pytest.fixture
def student_api(student):
    client = APIClient()
    client.force_authenticate(user=student)
    return client


@pytest.fixture
def lecturer_api(lecturer):
    client = APIClient()
    client.force_authenticate(user=lecturer)
    return client


@pytest.fixture
def admin_api(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def anon_api():
    return APIClient()


# ---------------------------------------------------------------------------
# Extended fixtures for matrix test cases (AS/AD/BD/GV)
# ---------------------------------------------------------------------------

@pytest.fixture
def completed_session(student, assessment):
    from assessment.services import evaluate_answer, complete_assessment
    from assessment.models import AssessmentSession, AssessmentResponse

    session = AssessmentSession.objects.create(
        student=student, assessment=assessment,
    )
    for q in assessment.questions.order_by("order"):
        AssessmentResponse.objects.create(
            session=session,
            question=q,
            answer="A",
            is_correct=evaluate_answer(q, "A"),
            time_taken_seconds=10,
        )
    profile = complete_assessment(session.id, student.id)
    session.refresh_from_db()
    return session, profile


@pytest.fixture
def student_with_pathway(student, course, concepts, milestones, micro_tasks):
    from adaptive.models import MasteryState, StudentPathway

    bkt = {
        "p_guess": 0.25, "p_slip": 0.10, "p_transit": 0.09,
    }
    for concept in concepts:
        MasteryState.objects.get_or_create(
            student=student, concept=concept,
            defaults={"p_mastery": 0.5, **bkt},
        )
    pathway, _ = StudentPathway.objects.get_or_create(
        student=student, course=course,
        defaults={
            "current_concept": concepts[0],
            "current_milestone": milestones[0],
        },
    )
    return pathway


@pytest.fixture
def lecturer_other(db):
    return User.objects.create_user(
        username="other_lecturer", password="Str0ngP@ss!",
        role=User.Role.LECTURER,
        first_name="Pham", last_name="Van D",
    )


@pytest.fixture
def lecturer_other_api(lecturer_other):
    client = APIClient()
    client.force_authenticate(user=lecturer_other)
    return client


@pytest.fixture
def bulk_students(db, student_class):
    students = []
    for i in range(5):
        s = User.objects.create_user(
            username=f"bulk_sv_{i}", password="Str0ngP@ss!",
            role=User.Role.STUDENT, student_id=f"22KT01{i:02d}",
        )
        ClassMembership.objects.create(student=s, student_class=student_class)
        students.append(s)
    return students
