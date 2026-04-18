"""
Comprehensive API contract tests — every core endpoint is verified for:
  - Correct HTTP status on happy path
  - Response body matches documented schema keys
  - X-Request-ID header present in response
  - Pagination shape for list endpoints

Coverage gate: 100 % of endpoints in API_CONTRACT.md.
"""

import uuid

import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.contract]

IDEM = str(uuid.uuid4())


def _idem():
    return str(uuid.uuid4())


def _assert_request_id(resp):
    assert "X-Request-ID" in resp, "Missing X-Request-ID header"


def _assert_paginated(data):
    if isinstance(data, dict) and "results" in data:
        assert "count" in data
        assert "next" in data or data["next"] is None
        assert "previous" in data or data["previous"] is None


class TestAuthContract:

    def test_login(self, student, anon_api):
        resp = anon_api.post("/api/auth/login/", {
            "username": student.username,
            "password": "Str0ngP@ss!",
        }, format="json")
        assert resp.status_code == 200
        assert "access" in resp.data
        assert "refresh" in resp.data
        _assert_request_id(resp)

    def test_login_wrong_password(self, student, anon_api):
        resp = anon_api.post("/api/auth/login/", {
            "username": student.username,
            "password": "wrong",
        }, format="json")
        assert resp.status_code == 401
        _assert_request_id(resp)

    def test_register(self, anon_api):
        resp = anon_api.post("/api/auth/register/", {
            "username": "new_user_contract",
            "email": "contract@test.vn",
            "password": "Str0ngP@ss!",
            "first_name": "Test",
            "last_name": "User",
            "student_id": "CT0001",
        }, format="json")
        assert resp.status_code == 201
        for key in ("id", "username", "email"):
            assert key in resp.data
        _assert_request_id(resp)

    def test_logout(self, student_api):
        resp = student_api.post("/api/auth/logout/")
        assert resp.status_code == 200
        _assert_request_id(resp)

    def test_profile_get(self, student_api):
        resp = student_api.get("/api/auth/profile/")
        assert resp.status_code == 200
        for key in ("id", "username", "role", "first_name", "last_name"):
            assert key in resp.data
        _assert_request_id(resp)

    def test_profile_put(self, student_api):
        resp = student_api.put("/api/auth/profile/", {
            "first_name": "Updated",
            "last_name": "Name",
            "email": "updated@test.vn",
            "username": "test_student",
        }, format="json")
        assert resp.status_code == 200
        assert resp.data["first_name"] == "Updated"
        _assert_request_id(resp)

    def test_consent(self, student_api):
        resp = student_api.post("/api/auth/consent/", {
            "consent_given": True,
        }, format="json")
        assert resp.status_code == 200
        _assert_request_id(resp)

    def test_classes_list(self, lecturer_api):
        resp = lecturer_api.get("/api/auth/classes/")
        assert resp.status_code == 200
        _assert_paginated(resp.data)
        _assert_request_id(resp)

    def test_class_students(self, lecturer_api, class_with_members):
        resp = lecturer_api.get(
            f"/api/auth/classes/{class_with_members.pk}/students/"
        )
        assert resp.status_code == 200
        _assert_request_id(resp)


class TestAssessmentContract:

    def test_list(self, student_api, assessment):
        resp = student_api.get("/api/assessment/")
        assert resp.status_code == 200
        _assert_paginated(resp.data)
        _assert_request_id(resp)

    def test_questions(self, student_api, assessment):
        resp = student_api.get(f"/api/assessment/{assessment.pk}/questions/")
        assert resp.status_code == 200
        _assert_request_id(resp)

    def test_start(self, student_api, assessment):
        resp = student_api.post(
            f"/api/assessment/{assessment.pk}/start/",
            HTTP_IDEMPOTENCY_KEY=_idem(),
        )
        assert resp.status_code == 201
        for key in ("id", "status"):
            assert key in resp.data
        _assert_request_id(resp)

    def test_my_sessions(self, student_api):
        resp = student_api.get("/api/assessment/my-sessions/")
        assert resp.status_code == 200
        _assert_request_id(resp)


class TestCurriculumContract:

    def test_courses_list(self, student_api, course):
        resp = student_api.get("/api/curriculum/courses/")
        assert resp.status_code == 200
        _assert_paginated(resp.data)
        _assert_request_id(resp)

    def test_course_detail(self, student_api, course):
        resp = student_api.get(f"/api/curriculum/courses/{course.pk}/")
        assert resp.status_code == 200
        _assert_request_id(resp)

    def test_concepts(self, student_api, course, concepts):
        resp = student_api.get(f"/api/curriculum/courses/{course.pk}/concepts/")
        assert resp.status_code == 200
        _assert_request_id(resp)

    def test_milestones(self, student_api, course, milestones):
        resp = student_api.get(f"/api/curriculum/courses/{course.pk}/milestones/")
        assert resp.status_code == 200
        _assert_request_id(resp)

    def test_milestone_detail(self, student_api, milestones):
        resp = student_api.get(f"/api/curriculum/milestones/{milestones[0].pk}/")
        assert resp.status_code == 200
        _assert_request_id(resp)

    def test_tasks_list(self, student_api, micro_tasks):
        resp = student_api.get("/api/curriculum/tasks/")
        assert resp.status_code == 200
        _assert_paginated(resp.data)
        _assert_request_id(resp)

    def test_supplementary_content(self, student_api, concepts, supplementary):
        resp = student_api.get(
            f"/api/curriculum/concepts/{concepts[0].pk}/content/"
        )
        assert resp.status_code == 200
        _assert_request_id(resp)

    def test_my_enrollments(self, student_api):
        resp = student_api.get("/api/curriculum/my-enrollments/")
        assert resp.status_code == 200
        _assert_request_id(resp)


class TestAdaptiveContract:

    def test_submit(self, student_api, micro_tasks):
        task = micro_tasks[0]
        resp = student_api.post("/api/adaptive/submit/", {
            "task_id": task.pk,
            "answer": task.content["correct_answer"],
            "duration_seconds": 30,
            "hints_used": 0,
        }, format="json", HTTP_IDEMPOTENCY_KEY=_idem())
        assert resp.status_code == 200
        for key in ("attempt", "mastery", "pathway"):
            assert key in resp.data
        _assert_request_id(resp)

    def test_mastery_list(self, student_api, student, concepts):
        from adaptive.models import MasteryState
        MasteryState.objects.create(
            student=student, concept=concepts[0], p_mastery=0.5
        )
        resp = student_api.get("/api/adaptive/mastery/")
        assert resp.status_code == 200
        _assert_request_id(resp)

    def test_pathway(self, student_api, course):
        resp = student_api.get(f"/api/adaptive/pathway/{course.pk}/")
        assert resp.status_code == 200
        _assert_request_id(resp)

    def test_next_task(self, student_api, course, micro_tasks):
        from adaptive.models import StudentPathway
        StudentPathway.objects.create(
            student=self._get_user(student_api),
            course=course,
            current_concept=micro_tasks[0].concept,
        )
        resp = student_api.get(f"/api/adaptive/next-task/{course.pk}/")
        assert resp.status_code == 200
        _assert_request_id(resp)

    def test_attempts(self, student_api):
        resp = student_api.get("/api/adaptive/attempts/")
        assert resp.status_code == 200
        _assert_request_id(resp)

    def test_interventions(self, student_api):
        resp = student_api.get("/api/adaptive/interventions/")
        assert resp.status_code == 200
        _assert_request_id(resp)

    def test_student_mastery_lecturer(
        self, lecturer_api, student, class_with_members, concepts,
    ):
        from adaptive.models import MasteryState
        MasteryState.objects.create(
            student=student, concept=concepts[0], p_mastery=0.5,
        )
        resp = lecturer_api.get(
            f"/api/adaptive/student/{student.pk}/mastery/"
        )
        assert resp.status_code == 200
        _assert_request_id(resp)

    @staticmethod
    def _get_user(api_client):
        return api_client.handler._force_user


class TestDashboardContract:

    def test_overview(self, lecturer_api, class_with_members):
        resp = lecturer_api.get(
            f"/api/dashboard/class/{class_with_members.pk}/overview/"
        )
        assert resp.status_code == 200
        for key in (
            "total_students", "on_track", "needs_attention",
            "needs_intervention",
        ):
            assert key in resp.data
        _assert_request_id(resp)

    def test_alerts_list(self, lecturer_api, class_with_members):
        resp = lecturer_api.get("/api/dashboard/alerts/")
        assert resp.status_code == 200
        _assert_paginated(resp.data)
        _assert_request_id(resp)

    def test_interventions_history(self, lecturer_api, class_with_members):
        resp = lecturer_api.get("/api/dashboard/interventions/history/")
        assert resp.status_code == 200
        _assert_paginated(resp.data)
        _assert_request_id(resp)


class TestEventsContract:

    def test_track(self, student_api):
        resp = student_api.post("/api/events/track/", {
            "event_name": "session_started",
            "properties": {"page": "/test"},
        }, format="json")
        assert resp.status_code == 201
        _assert_request_id(resp)

    def test_batch(self, student_api):
        resp = student_api.post("/api/events/batch/", {
            "events": [
                {"event_name": "page_view", "properties": {"page": "/a"}},
                {"event_name": "page_view", "properties": {"page": "/b"}},
            ],
        }, format="json")
        assert resp.status_code == 201
        assert "tracked" in resp.data
        _assert_request_id(resp)

    def test_my_events(self, student_api):
        resp = student_api.get("/api/events/my/")
        assert resp.status_code == 200
        _assert_request_id(resp)

    def test_student_events_lecturer(
        self, lecturer_api, student, class_with_members,
    ):
        resp = lecturer_api.get(f"/api/events/student/{student.pk}/")
        assert resp.status_code == 200
        _assert_request_id(resp)


class TestWellbeingContract:

    def test_check_no_nudge(self, student_api):
        resp = student_api.post("/api/wellbeing/check/", {
            "continuous_minutes": 30,
        }, format="json")
        assert resp.status_code == 200
        assert "should_nudge" in resp.data
        assert resp.data["should_nudge"] is False
        _assert_request_id(resp)

    def test_check_with_nudge(self, student_api):
        resp = student_api.post("/api/wellbeing/check/", {
            "continuous_minutes": 55,
        }, format="json")
        assert resp.status_code == 200
        assert resp.data["should_nudge"] is True
        assert "nudge" in resp.data
        _assert_request_id(resp)

    def test_my_nudges(self, student_api):
        resp = student_api.get("/api/wellbeing/my/")
        assert resp.status_code == 200
        _assert_request_id(resp)


class TestAnalyticsContract:

    def test_kpi(self, lecturer_api, class_with_members):
        resp = lecturer_api.get(
            f"/api/analytics/kpi/{class_with_members.pk}/"
        )
        assert resp.status_code == 200
        _assert_request_id(resp)

    def test_reports_list(self, admin_api):
        resp = admin_api.get("/api/analytics/reports/")
        assert resp.status_code == 200
        _assert_paginated(resp.data)
        _assert_request_id(resp)

    def test_data_quality(self, admin_api):
        resp = admin_api.get("/api/analytics/data-quality/")
        assert resp.status_code == 200
        _assert_paginated(resp.data)
        _assert_request_id(resp)


class TestPrivacyContract:

    def test_consent_get(self, student_api):
        resp = student_api.get("/api/privacy/consent/")
        assert resp.status_code == 200
        _assert_request_id(resp)

    def test_consent_post(self, student_api):
        resp = student_api.post("/api/privacy/consent/", {
            "consents": [{"purpose": "academic", "granted": True}],
        }, format="json")
        assert resp.status_code == 200
        _assert_request_id(resp)

    def test_consent_history(self, student_api):
        resp = student_api.get("/api/privacy/consent/history/")
        assert resp.status_code == 200
        _assert_request_id(resp)

    def test_export(self, student_api):
        resp = student_api.get("/api/privacy/export/")
        assert resp.status_code == 200
        assert "meta" in resp.data
        assert "data" in resp.data
        _assert_request_id(resp)

    def test_deletion_requests(self, student_api):
        resp = student_api.get("/api/privacy/delete/requests/")
        assert resp.status_code == 200
        _assert_request_id(resp)

    def test_audit_log(self, student_api):
        resp = student_api.get("/api/privacy/audit-log/")
        assert resp.status_code == 200
        _assert_request_id(resp)

    def test_incidents_list(self, admin_api):
        resp = admin_api.get("/api/privacy/incidents/")
        assert resp.status_code == 200
        _assert_request_id(resp)

    def test_incidents_create(self, admin_api):
        resp = admin_api.post("/api/privacy/incidents/", {
            "severity": "low",
            "title": "Test incident",
            "description": "Contract test incident",
        }, format="json")
        assert resp.status_code == 201
        _assert_request_id(resp)


class TestHealthContract:

    def test_liveness(self, anon_api):
        resp = anon_api.get("/api/health/")
        assert resp.status_code == 200
        assert resp.data.get("status") == "ok"
        _assert_request_id(resp)

    def test_readiness(self, anon_api):
        resp = anon_api.get("/api/health/ready/")
        assert resp.status_code in (200, 503)
        _assert_request_id(resp)

    def test_deep_health(self, admin_api):
        resp = admin_api.get("/api/health/deep/")
        # 503 is acceptable when subsystems (Celery worker, beat heartbeat)
        # aren't available in test env -- the contract is that admins can
        # reach the endpoint.
        assert resp.status_code in (200, 503)
        _assert_request_id(resp)
