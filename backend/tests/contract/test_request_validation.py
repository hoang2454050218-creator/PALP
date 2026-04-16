import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.contract]


class TestAdaptiveValidation:

    def test_submit_missing_task_id(self, student_api):
        resp = student_api.post("/api/adaptive/submit/", {
            "answer": "A",
            "duration_seconds": 30,
        }, format="json")
        assert resp.status_code == 400

    def test_submit_negative_duration(self, student_api, micro_tasks):
        resp = student_api.post("/api/adaptive/submit/", {
            "task_id": micro_tasks[0].pk,
            "answer": "A",
            "duration_seconds": -1,
            "hints_used": 0,
        }, format="json")
        assert resp.status_code == 400


class TestAuthValidation:

    def test_login_missing_password(self, anon_api):
        resp = anon_api.post("/api/auth/login/", {
            "username": "someone",
        }, format="json")
        assert resp.status_code == 400


class TestEventValidation:

    def test_track_missing_event_name(self, student_api):
        resp = student_api.post("/api/events/track/", {
            "properties": {"page": "/test"},
        }, format="json")
        assert resp.status_code == 400


class TestWellbeingValidation:

    def test_check_missing_minutes(self, student_api):
        resp = student_api.post("/api/wellbeing/check/", {}, format="json")
        assert resp.status_code == 400
