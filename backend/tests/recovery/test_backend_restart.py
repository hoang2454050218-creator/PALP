"""
Recovery test: Backend restart mid-session.

Verifies that when the Django process restarts mid-session:
  - In-progress assessment sessions survive (stored in DB)
  - Submitted answers are preserved
  - Student can resume and complete the assessment
  - Mastery state is not lost
"""
import pytest

from django.core.cache import cache

from assessment.models import AssessmentSession, AssessmentResponse
from adaptive.engine import get_mastery_state, update_mastery
from adaptive.models import MasteryState

pytestmark = [pytest.mark.django_db, pytest.mark.recovery]


class TestAssessmentSessionSurvivesRestart:
    """Assessment state must persist across process restarts."""

    def test_session_retrievable_after_cache_flush(
        self, student_api, student, assessment,
    ):
        resp = student_api.post(f"/api/assessment/{assessment.id}/start/")
        assert resp.status_code == 201
        session_id = resp.json()["id"]

        question = assessment.questions.first()
        student_api.post(
            f"/api/assessment/sessions/{session_id}/answer/",
            data={"question_id": question.id, "answer": "A", "time_taken_seconds": 10},
        )

        cache.clear()

        session = AssessmentSession.objects.get(id=session_id)
        assert session.status == AssessmentSession.Status.IN_PROGRESS
        assert session.responses.count() == 1

    def test_answers_preserved_after_flush(
        self, student_api, student, assessment,
    ):
        resp = student_api.post(f"/api/assessment/{assessment.id}/start/")
        session_id = resp.json()["id"]

        questions = list(assessment.questions.all())
        for q in questions[:2]:
            student_api.post(
                f"/api/assessment/sessions/{session_id}/answer/",
                data={"question_id": q.id, "answer": "A", "time_taken_seconds": 15},
            )

        cache.clear()

        responses = AssessmentResponse.objects.filter(session_id=session_id)
        assert responses.count() == 2
        for r in responses:
            assert r.answer == "A"
            assert r.time_taken_seconds == 15

    def test_can_complete_after_restart(
        self, student_api, student, assessment,
    ):
        resp = student_api.post(f"/api/assessment/{assessment.id}/start/")
        session_id = resp.json()["id"]

        for q in assessment.questions.all():
            student_api.post(
                f"/api/assessment/sessions/{session_id}/answer/",
                data={"question_id": q.id, "answer": "A", "time_taken_seconds": 10},
            )

        cache.clear()

        resp = student_api.post(
            f"/api/assessment/sessions/{session_id}/complete/"
        )
        assert resp.status_code == 200

        session = AssessmentSession.objects.get(id=session_id)
        assert session.status == AssessmentSession.Status.COMPLETED
        assert session.total_score is not None


class TestMasteryStateSurvivesRestart:
    """BKT mastery state must persist across process restarts."""

    def test_mastery_persisted_in_db(self, student, concepts):
        state = update_mastery(student.id, concepts[0].id, is_correct=True)
        original_p = state.p_mastery

        cache.clear()

        db_state = MasteryState.objects.get(student=student, concept=concepts[0])
        assert db_state.p_mastery == pytest.approx(original_p)
        assert db_state.attempt_count == 1
        assert db_state.correct_count == 1

    def test_sequential_updates_persist(self, student, concepts):
        for correct in [True, False, True, True, True]:
            update_mastery(student.id, concepts[0].id, is_correct=correct)

        cache.clear()

        db_state = MasteryState.objects.get(student=student, concept=concepts[0])
        assert db_state.attempt_count == 5
        assert db_state.correct_count == 4
        assert 0.01 <= db_state.p_mastery <= 0.99

    def test_cache_rebuilds_after_restart(self, student, concepts):
        update_mastery(student.id, concepts[0].id, is_correct=True)
        cache.clear()

        key = f"mastery:{student.id}:{concepts[0].id}"
        assert cache.get(key) is None

        state = get_mastery_state(student.id, concepts[0].id)
        assert state.attempt_count == 1

        cached = cache.get(key)
        assert cached is not None
        assert cached.p_mastery == state.p_mastery
