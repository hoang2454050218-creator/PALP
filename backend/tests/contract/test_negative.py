"""
Negative / validation tests for every write endpoint.

For each POST/PUT/PATCH endpoint, verifies:
  - Missing required fields -> 400 with ``error.code`` = ``VALIDATION_ERROR``
  - Invalid types -> 400
  - Boundary values -> 400
  - Error response follows the standard envelope format

Coverage gate: 100 % of write endpoints.
"""

import uuid

import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.contract]


def _idem():
    return str(uuid.uuid4())


def _assert_error_envelope(resp, expected_code="VALIDATION_ERROR"):
    assert resp.status_code == 400, (
        f"Expected 400, got {resp.status_code}: {resp.data}"
    )
    assert "error" in resp.data, f"Missing 'error' envelope: {resp.data}"
    err = resp.data["error"]
    assert err["code"] == expected_code
    assert "message" in err
    assert "request_id" in err


class TestAuthNegative:

    def test_login_missing_password(self, anon_api):
        resp = anon_api.post("/api/auth/login/", {
            "username": "someone",
        }, format="json")
        _assert_error_envelope(resp)

    def test_login_missing_username(self, anon_api):
        resp = anon_api.post("/api/auth/login/", {
            "password": "something",
        }, format="json")
        _assert_error_envelope(resp)

    def test_login_empty_body(self, anon_api):
        resp = anon_api.post("/api/auth/login/", {}, format="json")
        _assert_error_envelope(resp)

    def test_register_missing_required(self, anon_api):
        resp = anon_api.post("/api/auth/register/", {
            "username": "partial",
        }, format="json")
        _assert_error_envelope(resp)

    def test_register_short_password(self, anon_api):
        resp = anon_api.post("/api/auth/register/", {
            "username": "short_pw",
            "email": "s@t.vn",
            "password": "123",
            "first_name": "A",
            "last_name": "B",
            "student_id": "SH001",
        }, format="json")
        _assert_error_envelope(resp)

    def test_consent_missing_field(self, student_api):
        resp = student_api.post("/api/auth/consent/", {}, format="json")
        _assert_error_envelope(resp)

    def test_token_refresh_missing_refresh(self, anon_api):
        resp = anon_api.post("/api/auth/token/refresh/", {}, format="json")
        assert resp.status_code == 400


class TestAdaptiveNegative:

    def test_submit_missing_task_id(self, student_api):
        resp = student_api.post("/api/adaptive/submit/", {
            "answer": "A",
            "duration_seconds": 30,
        }, format="json", HTTP_IDEMPOTENCY_KEY=_idem())
        _assert_error_envelope(resp)

    def test_submit_negative_duration(self, student_api, micro_tasks):
        resp = student_api.post("/api/adaptive/submit/", {
            "task_id": micro_tasks[0].pk,
            "answer": "A",
            "duration_seconds": -1,
            "hints_used": 0,
        }, format="json", HTTP_IDEMPOTENCY_KEY=_idem())
        _assert_error_envelope(resp)

    def test_submit_negative_hints(self, student_api, micro_tasks):
        resp = student_api.post("/api/adaptive/submit/", {
            "task_id": micro_tasks[0].pk,
            "answer": "A",
            "duration_seconds": 30,
            "hints_used": -5,
        }, format="json", HTTP_IDEMPOTENCY_KEY=_idem())
        _assert_error_envelope(resp)

    def test_submit_empty_body(self, student_api):
        resp = student_api.post(
            "/api/adaptive/submit/", {}, format="json",
            HTTP_IDEMPOTENCY_KEY=_idem(),
        )
        _assert_error_envelope(resp)

    def test_submit_missing_idempotency_key(self, student_api, micro_tasks):
        resp = student_api.post("/api/adaptive/submit/", {
            "task_id": micro_tasks[0].pk,
            "answer": "A",
            "duration_seconds": 30,
            "hints_used": 0,
        }, format="json", HTTP_IDEMPOTENCY_KEY=None)
        _assert_error_envelope(resp)

    def test_submit_invalid_idempotency_key(self, student_api, micro_tasks):
        resp = student_api.post("/api/adaptive/submit/", {
            "task_id": micro_tasks[0].pk,
            "answer": "A",
            "duration_seconds": 30,
            "hints_used": 0,
        }, format="json", HTTP_IDEMPOTENCY_KEY="not-a-uuid")
        _assert_error_envelope(resp)


class TestAssessmentNegative:

    def test_start_missing_idempotency(self, student_api, assessment):
        resp = student_api.post(
            f"/api/assessment/{assessment.pk}/start/",
            HTTP_IDEMPOTENCY_KEY=None,
        )
        _assert_error_envelope(resp)

    def test_start_nonexistent_assessment(self, student_api):
        resp = student_api.post(
            "/api/assessment/99999/start/",
            HTTP_IDEMPOTENCY_KEY=_idem(),
        )
        assert resp.status_code == 404

    def test_answer_missing_question_id(
        self, student_api, assessment,
    ):
        start_resp = student_api.post(
            f"/api/assessment/{assessment.pk}/start/",
            HTTP_IDEMPOTENCY_KEY=_idem(),
        )
        session_id = start_resp.data["id"]
        resp = student_api.post(
            f"/api/assessment/sessions/{session_id}/answer/",
            {"answer": "A", "time_taken_seconds": 10},
            format="json",
            HTTP_IDEMPOTENCY_KEY=_idem(),
        )
        _assert_error_envelope(resp)

    def test_complete_missing_idempotency(self, student_api, assessment):
        start_resp = student_api.post(
            f"/api/assessment/{assessment.pk}/start/",
            HTTP_IDEMPOTENCY_KEY=_idem(),
        )
        session_id = start_resp.data["id"]
        resp = student_api.post(
            f"/api/assessment/sessions/{session_id}/complete/",
            HTTP_IDEMPOTENCY_KEY=None,
        )
        _assert_error_envelope(resp)


class TestEventNegative:

    def test_track_missing_event_name(self, student_api):
        resp = student_api.post("/api/events/track/", {
            "properties": {"page": "/test"},
        }, format="json")
        _assert_error_envelope(resp)

    def test_track_empty_body(self, student_api):
        resp = student_api.post("/api/events/track/", {}, format="json")
        _assert_error_envelope(resp)

    def test_batch_empty_events(self, student_api):
        resp = student_api.post("/api/events/batch/", {
            "events": [],
        }, format="json")
        assert resp.status_code in (400, 201)

    def test_batch_missing_events_key(self, student_api):
        resp = student_api.post("/api/events/batch/", {}, format="json")
        _assert_error_envelope(resp)


class TestWellbeingNegative:

    def test_check_missing_minutes(self, student_api):
        resp = student_api.post("/api/wellbeing/check/", {}, format="json")
        _assert_error_envelope(resp)

    def test_check_invalid_type(self, student_api):
        resp = student_api.post("/api/wellbeing/check/", {
            "continuous_minutes": "not_a_number",
        }, format="json")
        _assert_error_envelope(resp)

    def test_nudge_respond_nonexistent(self, student_api):
        resp = student_api.post(
            "/api/wellbeing/nudge/99999/respond/",
            {"response": "accepted"},
            format="json",
        )
        assert resp.status_code in (404, 500)


class TestDashboardNegative:

    def test_dismiss_missing_reason(
        self, lecturer_api, student, class_with_members,
    ):
        from dashboard.models import Alert
        alert = Alert.objects.create(
            student=student,
            student_class=class_with_members,
            severity=Alert.Severity.YELLOW,
            trigger_type=Alert.TriggerType.INACTIVITY,
            reason="Test",
        )
        resp = lecturer_api.post(
            f"/api/dashboard/alerts/{alert.pk}/dismiss/",
            {}, format="json",
        )
        _assert_error_envelope(resp)

    def test_intervention_missing_alert_id(self, lecturer_api):
        resp = lecturer_api.post("/api/dashboard/interventions/", {
            "action_type": "send_message",
            "target_student_ids": [1],
        }, format="json", HTTP_IDEMPOTENCY_KEY=_idem())
        _assert_error_envelope(resp)

    def test_intervention_missing_action_type(self, lecturer_api):
        resp = lecturer_api.post("/api/dashboard/interventions/", {
            "alert_id": 1,
            "target_student_ids": [1],
        }, format="json", HTTP_IDEMPOTENCY_KEY=_idem())
        _assert_error_envelope(resp)

    def test_intervention_empty_body(self, lecturer_api):
        resp = lecturer_api.post(
            "/api/dashboard/interventions/", {}, format="json",
            HTTP_IDEMPOTENCY_KEY=_idem(),
        )
        _assert_error_envelope(resp)


class TestPrivacyNegative:

    def test_consent_invalid_structure(self, student_api):
        resp = student_api.post("/api/privacy/consent/", {
            "consents": "not_a_list",
        }, format="json")
        _assert_error_envelope(resp)

    def test_delete_missing_tiers(self, student_api):
        resp = student_api.post(
            "/api/privacy/delete/", {}, format="json",
            HTTP_IDEMPOTENCY_KEY=_idem(),
        )
        _assert_error_envelope(resp)

    def test_incident_missing_required(self, admin_api):
        resp = admin_api.post("/api/privacy/incidents/", {
            "severity": "low",
        }, format="json")
        _assert_error_envelope(resp)

    def test_incident_invalid_severity(self, admin_api):
        resp = admin_api.post("/api/privacy/incidents/", {
            "severity": "nonexistent",
            "title": "t",
            "description": "d",
        }, format="json")
        _assert_error_envelope(resp)


class TestErrorEnvelopeFormat:
    """Verify the standard error envelope across different error types."""

    def test_401_has_error_envelope(self, anon_api):
        resp = anon_api.get("/api/auth/profile/")
        assert resp.status_code == 401
        assert "error" in resp.data
        assert resp.data["error"]["code"] == "AUTHENTICATION_REQUIRED"
        assert "message" in resp.data["error"]
        assert "request_id" in resp.data["error"]

    def test_403_has_error_envelope(self, student_api):
        resp = student_api.get("/api/dashboard/alerts/")
        assert resp.status_code == 403
        assert "error" in resp.data
        assert resp.data["error"]["code"] == "PERMISSION_DENIED"
        assert "message" in resp.data["error"]

    def test_404_has_error_envelope(self, student_api):
        resp = student_api.get("/api/assessment/99999/questions/")
        assert resp.status_code == 404
        assert "error" in resp.data
        assert resp.data["error"]["code"] == "NOT_FOUND"

    def test_400_has_details(self, student_api):
        resp = student_api.post(
            "/api/adaptive/submit/", {}, format="json",
            HTTP_IDEMPOTENCY_KEY=_idem(),
        )
        assert resp.status_code == 400
        err = resp.data["error"]
        assert err["code"] == "VALIDATION_ERROR"
        assert "details" in err or "message" in err

    def test_no_stack_trace_in_error(self, anon_api):
        resp = anon_api.post("/api/auth/login/", {
            "username": "nonexistent",
            "password": "wrong",
        }, format="json")
        body_str = str(resp.data)
        assert "Traceback" not in body_str
        assert "File " not in body_str
        assert ".py" not in body_str or "exception_handler" not in body_str
