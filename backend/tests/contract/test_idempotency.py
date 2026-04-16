"""
Idempotency behaviour tests for write endpoints.

Verifies:
  - Same Idempotency-Key -> same response replayed, no duplicate record
  - Different Idempotency-Key -> new record created
  - Missing Idempotency-Key on required endpoints -> 400
  - Invalid Idempotency-Key format -> 400
  - Replayed response includes ``Idempotency-Replayed: true`` header

Coverage gate: 100 % of endpoints with idempotency policy.
"""

import uuid

import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.contract, pytest.mark.idempotency]


def _idem():
    return str(uuid.uuid4())


class TestAdaptiveIdempotency:

    def test_same_key_returns_identical_response(
        self, student_api, micro_tasks,
    ):
        task = micro_tasks[0]
        key = _idem()
        payload = {
            "task_id": task.pk,
            "answer": task.content["correct_answer"],
            "duration_seconds": 30,
            "hints_used": 0,
        }

        resp1 = student_api.post(
            "/api/adaptive/submit/", payload,
            format="json", HTTP_IDEMPOTENCY_KEY=key,
        )
        assert resp1.status_code == 200

        resp2 = student_api.post(
            "/api/adaptive/submit/", payload,
            format="json", HTTP_IDEMPOTENCY_KEY=key,
        )
        assert resp2.status_code == 200
        assert resp2.get("Idempotency-Replayed") == "true"
        assert resp2.data == resp1.data

    def test_different_key_creates_new_record(
        self, student_api, micro_tasks,
    ):
        task = micro_tasks[0]
        payload = {
            "task_id": task.pk,
            "answer": task.content["correct_answer"],
            "duration_seconds": 30,
            "hints_used": 0,
        }

        resp1 = student_api.post(
            "/api/adaptive/submit/", payload,
            format="json", HTTP_IDEMPOTENCY_KEY=_idem(),
        )
        resp2 = student_api.post(
            "/api/adaptive/submit/", payload,
            format="json", HTTP_IDEMPOTENCY_KEY=_idem(),
        )
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.data["attempt"]["id"] != resp2.data["attempt"]["id"]

    def test_missing_key_returns_400(self, student_api, micro_tasks):
        task = micro_tasks[0]
        resp = student_api.post("/api/adaptive/submit/", {
            "task_id": task.pk,
            "answer": task.content["correct_answer"],
            "duration_seconds": 30,
            "hints_used": 0,
        }, format="json")
        assert resp.status_code == 400
        assert resp.data["error"]["code"] == "VALIDATION_ERROR"

    def test_invalid_key_format_returns_400(self, student_api, micro_tasks):
        task = micro_tasks[0]
        resp = student_api.post("/api/adaptive/submit/", {
            "task_id": task.pk,
            "answer": "A",
            "duration_seconds": 30,
            "hints_used": 0,
        }, format="json", HTTP_IDEMPOTENCY_KEY="not-a-uuid")
        assert resp.status_code == 400


class TestAssessmentIdempotency:

    def test_start_same_key(self, student_api, assessment):
        key = _idem()
        resp1 = student_api.post(
            f"/api/assessment/{assessment.pk}/start/",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        assert resp1.status_code in (200, 201)

        resp2 = student_api.post(
            f"/api/assessment/{assessment.pk}/start/",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        assert resp2.get("Idempotency-Replayed") == "true"
        assert resp2.data["id"] == resp1.data["id"]

    def test_start_missing_key(self, student_api, assessment):
        resp = student_api.post(
            f"/api/assessment/{assessment.pk}/start/",
        )
        assert resp.status_code == 400

    def test_answer_same_key(self, student_api, assessment):
        session_resp = student_api.post(
            f"/api/assessment/{assessment.pk}/start/",
            HTTP_IDEMPOTENCY_KEY=_idem(),
        )
        session_id = session_resp.data["id"]
        question_id = assessment.questions.first().pk

        key = _idem()
        payload = {
            "question_id": question_id,
            "answer": "A",
            "time_taken_seconds": 10,
        }

        resp1 = student_api.post(
            f"/api/assessment/sessions/{session_id}/answer/",
            payload, format="json", HTTP_IDEMPOTENCY_KEY=key,
        )
        assert resp1.status_code == 200

        resp2 = student_api.post(
            f"/api/assessment/sessions/{session_id}/answer/",
            payload, format="json", HTTP_IDEMPOTENCY_KEY=key,
        )
        assert resp2.status_code == 200
        assert resp2.get("Idempotency-Replayed") == "true"

    def test_complete_same_key(self, student_api, assessment):
        session_resp = student_api.post(
            f"/api/assessment/{assessment.pk}/start/",
            HTTP_IDEMPOTENCY_KEY=_idem(),
        )
        session_id = session_resp.data["id"]

        key = _idem()
        resp1 = student_api.post(
            f"/api/assessment/sessions/{session_id}/complete/",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        assert resp1.status_code == 200

        resp2 = student_api.post(
            f"/api/assessment/sessions/{session_id}/complete/",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        assert resp2.status_code == 200
        assert resp2.get("Idempotency-Replayed") == "true"


class TestDashboardIdempotency:

    @pytest.fixture
    def alert(self, student, class_with_members):
        from dashboard.models import Alert
        return Alert.objects.create(
            student=student,
            student_class=class_with_members,
            severity=Alert.Severity.YELLOW,
            trigger_type=Alert.TriggerType.INACTIVITY,
            reason="Idempotency test",
        )

    def test_intervention_same_key(
        self, lecturer_api, alert, student, class_with_members,
    ):
        key = _idem()
        payload = {
            "alert_id": alert.pk,
            "action_type": "send_message",
            "target_student_ids": [student.pk],
            "message": "Test",
        }

        resp1 = lecturer_api.post(
            "/api/dashboard/interventions/",
            payload, format="json", HTTP_IDEMPOTENCY_KEY=key,
        )
        assert resp1.status_code == 201

        resp2 = lecturer_api.post(
            "/api/dashboard/interventions/",
            payload, format="json", HTTP_IDEMPOTENCY_KEY=key,
        )
        assert resp2.status_code == 201
        assert resp2.get("Idempotency-Replayed") == "true"
        assert resp2.data["id"] == resp1.data["id"]

    def test_intervention_missing_key(self, lecturer_api):
        resp = lecturer_api.post("/api/dashboard/interventions/", {
            "alert_id": 1,
            "action_type": "send_message",
            "target_student_ids": [1],
        }, format="json")
        assert resp.status_code == 400

    def test_dismiss_optional_key(
        self, lecturer_api, alert, class_with_members,
    ):
        resp = lecturer_api.post(
            f"/api/dashboard/alerts/{alert.pk}/dismiss/",
            {"dismiss_reason_code": "resolved"},
            format="json",
        )
        assert resp.status_code == 200


class TestWellbeingIdempotency:

    def test_check_optional_key(self, student_api):
        resp = student_api.post("/api/wellbeing/check/", {
            "continuous_minutes": 30,
        }, format="json")
        assert resp.status_code == 200

    def test_check_with_key_replays(self, student_api):
        key = _idem()
        resp1 = student_api.post("/api/wellbeing/check/", {
            "continuous_minutes": 30,
        }, format="json", HTTP_IDEMPOTENCY_KEY=key)
        assert resp1.status_code == 200

        resp2 = student_api.post("/api/wellbeing/check/", {
            "continuous_minutes": 30,
        }, format="json", HTTP_IDEMPOTENCY_KEY=key)
        assert resp2.status_code == 200
        assert resp2.get("Idempotency-Replayed") == "true"


class TestPrivacyIdempotency:

    def test_delete_missing_key(self, student_api):
        resp = student_api.post("/api/privacy/delete/", {
            "tiers": ["learning_data"],
        }, format="json")
        assert resp.status_code == 400

    def test_delete_with_key(self, student_api):
        key = _idem()
        resp = student_api.post("/api/privacy/delete/", {
            "tiers": ["learning_data"],
        }, format="json", HTTP_IDEMPOTENCY_KEY=key)
        assert resp.status_code in (200, 400)


class TestEventIdempotencyBuiltIn:
    """Events use built-in idempotency_key field, not HTTP header."""

    def test_track_with_idempotency_key(self, student_api):
        key = f"evt-{uuid.uuid4()}"
        payload = {
            "event_name": "session_started",
            "idempotency_key": key,
            "properties": {"page": "/test"},
        }
        resp1 = student_api.post(
            "/api/events/track/", payload, format="json",
        )
        assert resp1.status_code == 201

        resp2 = student_api.post(
            "/api/events/track/", payload, format="json",
        )
        assert resp2.status_code == 201
        assert resp2.data["id"] == resp1.data["id"]

    def test_track_without_idempotency_key(self, student_api):
        resp = student_api.post("/api/events/track/", {
            "event_name": "page_view",
            "properties": {"page": "/test"},
        }, format="json")
        assert resp.status_code == 201
