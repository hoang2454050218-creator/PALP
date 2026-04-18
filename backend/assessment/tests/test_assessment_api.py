import uuid

import pytest

from assessment.models import AssessmentSession

pytestmark = pytest.mark.django_db

URL = "/api/assessment/"


def _idem_header():
    return {"HTTP_IDEMPOTENCY_KEY": str(uuid.uuid4())}


class TestAssessmentList:
    def test_list_returns_200(self, student_api, assessment):
        resp = student_api.get(URL)
        assert resp.status_code == 200
        assert len(resp.data["results"]) >= 1

    def test_unauthenticated_returns_401(self, anon_api):
        resp = anon_api.get(URL)
        assert resp.status_code == 401


class TestStartAssessment:
    def test_start_creates_session(self, student_api, assessment):
        resp = student_api.post(f"{URL}{assessment.id}/start/", **_idem_header())
        assert resp.status_code == 201
        assert resp.data["status"] == "in_progress"

    def test_start_again_returns_existing(self, student_api, assessment):
        r1 = student_api.post(f"{URL}{assessment.id}/start/", **_idem_header())
        r2 = student_api.post(f"{URL}{assessment.id}/start/", **_idem_header())
        assert r2.status_code == 200
        assert r1.data["id"] == r2.data["id"]


class TestAssessmentQuestions:
    def test_returns_questions(self, student_api, assessment):
        resp = student_api.get(f"{URL}{assessment.id}/questions/")
        assert resp.status_code == 200
        assert len(resp.data["results"]) == 3


class TestSubmitAnswerAPI:
    def test_submit_answer(self, student_api, assessment):
        start = student_api.post(f"{URL}{assessment.id}/start/", **_idem_header())
        session_id = start.data["id"]
        q_id = assessment.questions.first().id

        resp = student_api.post(
            f"{URL}sessions/{session_id}/answer/",
            {"question_id": q_id, "answer": "A", "time_taken_seconds": 5},
            format="json",
            **_idem_header(),
        )
        assert resp.status_code == 200
        assert resp.data["is_correct"] is True


class TestCompleteAssessmentAPI:
    def test_complete_returns_profile(self, student_api, assessment):
        start = student_api.post(f"{URL}{assessment.id}/start/", **_idem_header())
        session_id = start.data["id"]

        for q in assessment.questions.order_by("order"):
            student_api.post(
                f"{URL}sessions/{session_id}/answer/",
                {"question_id": q.id, "answer": "A", "time_taken_seconds": 5},
                format="json",
                **_idem_header(),
            )

        resp = student_api.post(f"{URL}sessions/{session_id}/complete/", **_idem_header())
        assert resp.status_code == 200
        assert "profile" in resp.data


class TestMySessionsAPI:
    def test_my_sessions(self, student_api, student, assessment):
        AssessmentSession.objects.create(student=student, assessment=assessment)
        resp = student_api.get(f"{URL}my-sessions/")
        assert resp.status_code == 200
        assert len(resp.data["results"]) >= 1
