import pytest

from adaptive.models import MasteryState, TaskAttempt

pytestmark = pytest.mark.django_db

URL = "/api/adaptive/"


class TestMyMastery:
    def test_student_mastery_returns_200(self, student_api, student, concepts):
        MasteryState.objects.create(
            student=student, concept=concepts[0], p_mastery=0.5,
        )
        resp = student_api.get(f"{URL}mastery/")
        assert resp.status_code == 200
        assert len(resp.data["results"]) >= 1


class TestSubmitTaskAttempt:
    def test_correct_answer(self, student_api, student, micro_tasks):
        task = micro_tasks[0]
        resp = student_api.post(
            f"{URL}submit/",
            {
                "task_id": task.id,
                "answer": task.content["correct_answer"],
                "duration_seconds": 30,
                "hints_used": 0,
            },
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["attempt"]["is_correct"] is True

    def test_correct_answer_increases_mastery(self, student_api, student, micro_tasks):
        task = micro_tasks[0]
        student_api.post(
            f"{URL}submit/",
            {
                "task_id": task.id,
                "answer": task.content["correct_answer"],
                "duration_seconds": 30,
                "hints_used": 0,
            },
            format="json",
        )
        mastery = MasteryState.objects.get(
            student=student, concept=task.concept,
        )
        assert mastery.p_mastery > 0.3

    def test_wrong_answer(self, student_api, micro_tasks):
        task = micro_tasks[0]
        resp = student_api.post(
            f"{URL}submit/",
            {
                "task_id": task.id,
                "answer": "wrong",
                "duration_seconds": 15,
                "hints_used": 0,
            },
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["attempt"]["is_correct"] is False

    def test_attempt_number_increments(self, student_api, student, micro_tasks):
        task = micro_tasks[0]
        payload = {
            "task_id": task.id,
            "answer": task.content["correct_answer"],
            "duration_seconds": 10,
            "hints_used": 0,
        }

        r1 = student_api.post(f"{URL}submit/", payload, format="json")
        r2 = student_api.post(f"{URL}submit/", payload, format="json")

        assert r1.data["attempt"]["attempt_number"] == 1
        assert r2.data["attempt"]["attempt_number"] == 2
        assert TaskAttempt.objects.filter(student=student, task=task).count() == 2


class TestMyPathway:
    def test_pathway_returns_200(self, student_api, course):
        resp = student_api.get(f"{URL}pathway/{course.id}/")
        assert resp.status_code == 200
        assert resp.data["course"] == course.id


class TestMyAttempts:
    def test_attempts_returns_200(self, student_api, student, micro_tasks):
        task = micro_tasks[0]
        TaskAttempt.objects.create(
            student=student,
            task=task,
            score=100,
            max_score=100,
            is_correct=True,
            answer=task.content["correct_answer"],
            attempt_number=1,
        )
        resp = student_api.get(f"{URL}attempts/")
        assert resp.status_code == 200
        assert len(resp.data["results"]) >= 1


class TestMyInterventions:
    def test_interventions_returns_200(self, student_api):
        resp = student_api.get(f"{URL}interventions/")
        assert resp.status_code == 200


class TestStudentMastery:
    def test_lecturer_can_view_student_mastery(
        self, lecturer_api, student, concepts, class_with_members,
    ):
        MasteryState.objects.create(
            student=student, concept=concepts[0], p_mastery=0.7,
        )
        resp = lecturer_api.get(f"{URL}student/{student.id}/mastery/")
        assert resp.status_code == 200
        assert len(resp.data["results"]) >= 1

    def test_student_cannot_view_other_student_mastery(
        self, student_api, student_b,
    ):
        resp = student_api.get(f"{URL}student/{student_b.id}/mastery/")
        assert resp.status_code == 403
