import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.contract]


class TestAuthSchemas:

    def test_login_response_has_tokens(self, student, anon_api):
        resp = anon_api.post("/api/auth/login/", {
            "username": student.username,
            "password": "Str0ngP@ss!",
        }, format="json")
        assert resp.status_code == 200
        assert "access" in resp.data
        assert "refresh" in resp.data

    def test_login_wrong_password_returns_401(self, student, anon_api):
        resp = anon_api.post("/api/auth/login/", {
            "username": student.username,
            "password": "wrong",
        }, format="json")
        assert resp.status_code == 401

    def test_profile_response_schema(self, student_api):
        resp = student_api.get("/api/auth/profile/")
        assert resp.status_code == 200
        for key in ("id", "username", "role", "first_name", "last_name"):
            assert key in resp.data


class TestAssessmentSchemas:

    def test_assessment_list_has_pagination(self, student_api, assessment):
        resp = student_api.get("/api/assessment/")
        assert resp.status_code == 200
        if isinstance(resp.data, dict):
            for key in ("count", "results"):
                assert key in resp.data

    def test_assessment_start_response_schema(self, student_api, assessment):
        resp = student_api.post(f"/api/assessment/{assessment.pk}/start/")
        assert resp.status_code == 201
        assert "id" in resp.data
        assert "status" in resp.data


class TestAdaptiveSchemas:

    def test_submit_response_has_three_sections(
        self, student_api, micro_tasks,
    ):
        task = micro_tasks[0]
        resp = student_api.post("/api/adaptive/submit/", {
            "task_id": task.pk,
            "answer": task.content["correct_answer"],
            "duration_seconds": 30,
            "hints_used": 0,
        }, format="json")
        assert resp.status_code == 200
        assert "attempt" in resp.data
        assert "mastery" in resp.data
        assert "pathway" in resp.data

    def test_mastery_item_schema(self, student_api, student, concepts):
        from adaptive.models import MasteryState
        MasteryState.objects.create(student=student, concept=concepts[0], p_mastery=0.5)
        resp = student_api.get("/api/adaptive/mastery/")
        assert resp.status_code == 200
        results = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
        if results:
            item = results[0]
            for key in ("id", "concept", "p_mastery", "attempt_count", "correct_count"):
                assert key in item


class TestDashboardSchemas:

    def test_overview_response_schema(self, lecturer_api, class_with_members):
        resp = lecturer_api.get(
            f"/api/dashboard/class/{class_with_members.pk}/overview/",
        )
        assert resp.status_code == 200
        for key in ("total_students", "on_track", "needs_attention", "needs_intervention"):
            assert key in resp.data


class TestWellbeingSchemas:

    def test_check_no_nudge_response(self, student_api):
        resp = student_api.post(
            "/api/wellbeing/check/", {"continuous_minutes": 30}, format="json",
        )
        assert resp.status_code == 200
        assert "should_nudge" in resp.data
        assert resp.data["should_nudge"] is False

    def test_check_with_nudge_response(self, student_api):
        resp = student_api.post(
            "/api/wellbeing/check/", {"continuous_minutes": 55}, format="json",
        )
        assert resp.status_code == 200
        assert resp.data["should_nudge"] is True
        assert "nudge" in resp.data


class TestHealthCheck:

    def test_health_returns_200(self, anon_api):
        resp = anon_api.get("/api/health/")
        assert resp.status_code == 200
