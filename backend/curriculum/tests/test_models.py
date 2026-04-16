import pytest
from django.db import IntegrityError

from accounts.models import StudentClass
from curriculum.models import (
    Course,
    Concept,
    ConceptPrerequisite,
    Enrollment,
    Milestone,
    MicroTask,
    SupplementaryContent,
)

pytestmark = pytest.mark.django_db


class TestCourse:
    def test_creation_and_str(self, course):
        assert str(course) == "SBVL - Suc ben vat lieu"
        assert course.is_active is True
        assert course.credits == 3


class TestConcept:
    def test_ordering(self, concepts):
        codes = [c.code for c in Concept.objects.filter(course=concepts[0].course)]
        assert codes == ["NL", "US", "BD"]

    def test_prerequisite_chain(self, concepts):
        c1, c2, c3 = concepts

        assert c2.prerequisites.filter(prerequisite=c1).exists()
        assert c3.prerequisites.filter(prerequisite=c2).exists()
        assert not c1.prerequisites.exists()

    def test_str(self, concepts):
        assert str(concepts[0]) == "NL: Noi luc"


class TestMilestone:
    def test_ordering(self, milestones):
        titles = list(
            Milestone.objects.filter(course=milestones[0].course)
            .values_list("title", flat=True)
        )
        assert titles[0].startswith("M1")
        assert titles[1].startswith("M2")

    def test_concepts_m2m(self, milestones, concepts):
        assert milestones[0].concepts.count() == 1
        assert milestones[1].concepts.count() == 2
        assert concepts[0] in milestones[0].concepts.all()


class TestMicroTask:
    def test_difficulty_levels(self, milestones, concepts):
        for level, _ in MicroTask.DifficultyLevel.choices:
            task = MicroTask.objects.create(
                milestone=milestones[0],
                concept=concepts[0],
                title=f"Task L{level}",
                difficulty=level,
                content={},
            )
            assert task.difficulty == level

    def test_task_types(self, milestones, concepts):
        for task_type, _ in MicroTask.TaskType.choices:
            task = MicroTask.objects.create(
                milestone=milestones[0],
                concept=concepts[0],
                title=f"Task {task_type}",
                task_type=task_type,
                content={},
            )
            assert task.task_type == task_type

    def test_str(self, micro_tasks):
        assert "(L1)" in str(micro_tasks[0])


class TestSupplementaryContent:
    def test_creation(self, supplementary):
        assert supplementary.title == "Giai thich noi luc"
        assert supplementary.content_type == SupplementaryContent.ContentType.TEXT
        assert str(supplementary) == "Giai thich noi luc"


class TestEnrollment:
    def test_unique_together(self, student, course, student_class):
        Enrollment.objects.create(
            student=student,
            course=course,
            student_class=student_class,
            semester="HK1-2025",
        )
        with pytest.raises(IntegrityError):
            Enrollment.objects.create(
                student=student,
                course=course,
                student_class=student_class,
                semester="HK1-2025",
            )
