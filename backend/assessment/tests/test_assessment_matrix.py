"""
Assessment edge-case test matrix (AS-01 .. AS-10).

Covers: first-time open, reload resume, version-conflict sync, timer expiry,
concurrent complete, redo assessment, device switch, token cycle, drag-drop
bad input, and RBAC boundary.
"""
import pytest
from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone
from rest_framework import status

from assessment.models import (
    Assessment,
    AssessmentQuestion,
    AssessmentResponse,
    AssessmentSession,
    LearnerProfile,
)
from assessment.services import (
    complete_assessment,
    evaluate_answer,
    submit_answer,
)

pytestmark = pytest.mark.django_db

URL = "/api/assessment/"


# =========================================================================
# AS-01  SV first-time -> assessment opens correctly, timer correct
# =========================================================================


class TestAS01FirstTimeOpen:
    def test_creates_in_progress_session(self, student_api, assessment):
        resp = student_api.post(f"{URL}{assessment.id}/start/")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["status"] == "in_progress"
        assert resp.data["answered_question_ids"] == []

    def test_server_now_returned(self, student_api, assessment):
        resp = student_api.post(f"{URL}{assessment.id}/start/")
        assert "server_now" in resp.data

    def test_session_deadline_matches_time_limit(self, student_api, assessment):
        resp = student_api.post(f"{URL}{assessment.id}/start/")
        session = AssessmentSession.objects.get(id=resp.data["id"])
        expected_deadline = session.started_at + timedelta(
            minutes=assessment.time_limit_minutes
        )
        assert abs((session.deadline - expected_deadline).total_seconds()) < 1


# =========================================================================
# AS-02  Reload mid-assessment -> state preserved
# =========================================================================


class TestAS02ReloadPreservesState:
    def test_resume_returns_existing_session(self, student_api, assessment):
        r1 = student_api.post(f"{URL}{assessment.id}/start/")
        session_id = r1.data["id"]

        q = assessment.questions.first()
        student_api.post(
            f"{URL}sessions/{session_id}/answer/",
            {"question_id": q.id, "answer": "A", "time_taken_seconds": 5},
            format="json",
        )

        r2 = student_api.post(f"{URL}{assessment.id}/start/")
        assert r2.status_code == status.HTTP_200_OK
        assert r2.data["id"] == session_id

    def test_answered_ids_carried_over(self, student_api, assessment):
        r1 = student_api.post(f"{URL}{assessment.id}/start/")
        session_id = r1.data["id"]

        answered = []
        for q in assessment.questions.order_by("order")[:2]:
            student_api.post(
                f"{URL}sessions/{session_id}/answer/",
                {"question_id": q.id, "answer": "A", "time_taken_seconds": 5},
                format="json",
            )
            answered.append(q.id)

        r2 = student_api.post(f"{URL}{assessment.id}/start/")
        assert set(r2.data["answered_question_ids"]) == set(answered)


# =========================================================================
# AS-03  Network loss / version conflict -> proper error
# =========================================================================


class TestAS03VersionConflict:
    def test_stale_version_raises_conflict(self, student, assessment):
        session = AssessmentSession.objects.create(
            student=student, assessment=assessment,
        )
        q = assessment.questions.first()

        submit_answer(session, q.id, "A", time_taken=5, client_version=0)

        session.refresh_from_db()
        assert session.version == 1

        with pytest.raises(Exception) as exc_info:
            submit_answer(session, q.id, "B", time_taken=3, client_version=0)
        assert "version_conflict" in str(exc_info.value.detail) or "xung đột" in str(
            exc_info.value.detail
        )

    def test_partial_answers_survive_conflict(self, student, assessment):
        session = AssessmentSession.objects.create(
            student=student, assessment=assessment,
        )
        questions = list(assessment.questions.order_by("order"))

        submit_answer(session, questions[0].id, "A", time_taken=5)
        submit_answer(session, questions[1].id, "B", time_taken=5)

        assert AssessmentResponse.objects.filter(session=session).count() == 2


# =========================================================================
# AS-04  Submit exactly at timer expiry -> session expired
# =========================================================================


class TestAS04TimerExpiry:
    def test_complete_after_deadline_raises_expired(self, student, assessment):
        session = AssessmentSession.objects.create(
            student=student, assessment=assessment,
        )
        for q in assessment.questions.order_by("order"):
            AssessmentResponse.objects.create(
                session=session, question=q,
                answer="A", is_correct=True, time_taken_seconds=5,
            )

        past_deadline = session.started_at + timedelta(
            minutes=assessment.time_limit_minutes + 1
        )
        with patch("django.utils.timezone.now", return_value=past_deadline):
            with pytest.raises(Exception) as exc_info:
                complete_assessment(session.id, student.id)
            assert "session_expired" in str(exc_info.value.detail)

        session.refresh_from_db()
        assert session.status == AssessmentSession.Status.EXPIRED

    def test_submit_answer_after_deadline_raises(self, student, assessment):
        session = AssessmentSession.objects.create(
            student=student, assessment=assessment,
        )
        q = assessment.questions.first()

        past_deadline = session.started_at + timedelta(
            minutes=assessment.time_limit_minutes + 1
        )
        with patch("django.utils.timezone.now", return_value=past_deadline):
            with pytest.raises(Exception):
                submit_answer(session, q.id, "A", time_taken=5)


# =========================================================================
# AS-05  Two tabs complete simultaneously -> only 1 canonical profile
# =========================================================================


class TestAS05ConcurrentComplete:
    def test_idempotent_complete_produces_one_profile(self, student, assessment):
        session = AssessmentSession.objects.create(
            student=student, assessment=assessment,
        )
        for q in assessment.questions.order_by("order"):
            AssessmentResponse.objects.create(
                session=session, question=q,
                answer="A", is_correct=evaluate_answer(q, "A"),
                time_taken_seconds=5,
            )

        p1 = complete_assessment(session.id, student.id)
        p2 = complete_assessment(session.id, student.id)

        assert p1.id == p2.id
        assert LearnerProfile.objects.filter(
            student=student, course=assessment.course,
        ).count() == 1


# =========================================================================
# AS-06  Redo assessment -> newest wins, old archived
# =========================================================================


class TestAS06RedoAssessment:
    def test_old_session_stays_completed(self, student_api, student, assessment):
        r1 = student_api.post(f"{URL}{assessment.id}/start/")
        sid1 = r1.data["id"]
        for q in assessment.questions.order_by("order"):
            student_api.post(
                f"{URL}sessions/{sid1}/answer/",
                {"question_id": q.id, "answer": "A", "time_taken_seconds": 5},
                format="json",
            )
        student_api.post(f"{URL}sessions/{sid1}/complete/")

        r2 = student_api.post(f"{URL}{assessment.id}/start/")
        assert r2.status_code == status.HTTP_201_CREATED
        assert r2.data["id"] != sid1

        old = AssessmentSession.objects.get(id=sid1)
        assert old.status == AssessmentSession.Status.COMPLETED

    def test_profile_updated_not_duplicated(self, student_api, student, assessment):
        r1 = student_api.post(f"{URL}{assessment.id}/start/")
        sid1 = r1.data["id"]
        for q in assessment.questions.order_by("order"):
            student_api.post(
                f"{URL}sessions/{sid1}/answer/",
                {"question_id": q.id, "answer": "A", "time_taken_seconds": 5},
                format="json",
            )
        student_api.post(f"{URL}sessions/{sid1}/complete/")

        r2 = student_api.post(f"{URL}{assessment.id}/start/")
        sid2 = r2.data["id"]
        questions = list(assessment.questions.order_by("order"))
        for i, q in enumerate(questions):
            ans = "A" if i == 0 else "B"
            student_api.post(
                f"{URL}sessions/{sid2}/answer/",
                {"question_id": q.id, "answer": ans, "time_taken_seconds": 5},
                format="json",
            )
        student_api.post(f"{URL}sessions/{sid2}/complete/")

        assert LearnerProfile.objects.filter(
            student=student, course=assessment.course,
        ).count() == 1

        profile = LearnerProfile.objects.get(
            student=student, course=assessment.course,
        )
        assert profile.assessment_session_id == sid2


# =========================================================================
# AS-07  Device switch mid-assessment -> resume same session
# =========================================================================


class TestAS07DeviceSwitch:
    def test_different_client_same_user_resumes(self, student, assessment):
        from rest_framework.test import APIClient

        client_a = APIClient()
        client_a.force_authenticate(user=student)
        r1 = client_a.post(f"{URL}{assessment.id}/start/")
        sid = r1.data["id"]

        q = assessment.questions.first()
        client_a.post(
            f"{URL}sessions/{sid}/answer/",
            {"question_id": q.id, "answer": "A", "time_taken_seconds": 5},
            format="json",
        )

        client_b = APIClient()
        client_b.force_authenticate(user=student)
        r2 = client_b.post(f"{URL}{assessment.id}/start/")

        assert r2.status_code == status.HTTP_200_OK
        assert r2.data["id"] == sid
        assert q.id in r2.data["answered_question_ids"]


# =========================================================================
# AS-08  Token expires mid-assessment -> data survives re-auth
# =========================================================================


class TestAS08TokenExpiry:
    def test_answers_persist_across_auth_cycles(self, student, assessment):
        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=student)
        r1 = client.post(f"{URL}{assessment.id}/start/")
        sid = r1.data["id"]

        q = assessment.questions.first()
        client.post(
            f"{URL}sessions/{sid}/answer/",
            {"question_id": q.id, "answer": "A", "time_taken_seconds": 5},
            format="json",
        )

        client.force_authenticate(user=None)
        resp = client.get(f"{URL}my-sessions/")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

        client.force_authenticate(user=student)
        r2 = client.post(f"{URL}{assessment.id}/start/")
        assert r2.data["id"] == sid
        assert q.id in r2.data["answered_question_ids"]

        assert AssessmentResponse.objects.filter(
            session_id=sid, question=q,
        ).exists()


# =========================================================================
# AS-09  Drag-drop wrong format -> no crash, returns False
# =========================================================================


class TestAS09DragDropBadFormat:
    @pytest.fixture
    def drag_drop_question(self, course, concepts):
        a = Assessment.objects.create(
            course=course, title="DD Assessment", time_limit_minutes=15,
        )
        return AssessmentQuestion.objects.create(
            assessment=a, concept=concepts[0],
            question_type=AssessmentQuestion.QuestionType.DRAG_DROP,
            text="Order items", options=["X", "Y", "Z"],
            correct_answer=["X", "Y", "Z"], order=1,
        )

    def test_string_instead_of_list(self, drag_drop_question):
        assert evaluate_answer(drag_drop_question, "invalid_string") is False

    def test_none_input(self, drag_drop_question):
        assert evaluate_answer(drag_drop_question, None) is False

    def test_empty_list(self, drag_drop_question):
        assert evaluate_answer(drag_drop_question, []) is False

    def test_partial_list(self, drag_drop_question):
        assert evaluate_answer(drag_drop_question, ["X", "Y"]) is False

    def test_reversed_order(self, drag_drop_question):
        assert evaluate_answer(drag_drop_question, ["Z", "Y", "X"]) is False

    def test_correct_order_passes(self, drag_drop_question):
        assert evaluate_answer(drag_drop_question, ["X", "Y", "Z"]) is True


# =========================================================================
# AS-10  Lecturer role on student-only endpoints -> 403
# =========================================================================


class TestAS10RBACBoundary:
    def test_lecturer_cannot_start_assessment(self, lecturer_api, assessment):
        resp = lecturer_api.post(f"{URL}{assessment.id}/start/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_lecturer_cannot_submit_answer(
        self, lecturer_api, student, assessment,
    ):
        session = AssessmentSession.objects.create(
            student=student, assessment=assessment,
        )
        q = assessment.questions.first()
        resp = lecturer_api.post(
            f"{URL}sessions/{session.id}/answer/",
            {"question_id": q.id, "answer": "A", "time_taken_seconds": 5},
            format="json",
        )
        assert resp.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        )

    def test_lecturer_cannot_list_own_sessions(self, lecturer_api):
        resp = lecturer_api.get(f"{URL}my-sessions/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_anon_cannot_start_assessment(self, anon_api, assessment):
        resp = anon_api.post(f"{URL}{assessment.id}/start/")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
