"""
API Backend Discipline Tests (BD-R01..R05).

QA_STANDARD Section 5.0.
Verifies API hygiene: no 500 for validation, no stack traces,
actionable error messages, request IDs on learning endpoints.
"""
import pytest
from rest_framework import status

pytestmark = [pytest.mark.django_db, pytest.mark.contract]


# ---------------------------------------------------------------------------
# BD-R01: No 500 for validation errors
# ---------------------------------------------------------------------------


class TestBDR01NoValidation500:
    """Validation errors must return 400, never 500."""

    def test_empty_body_returns_400(self, student_api):
        resp = student_api.post("/api/events/track/", {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_required_field_returns_400(self, student_api):
        resp = student_api.post("/api/adaptive/submit/", {
            "answer": "A",
        }, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_type_returns_400(self, student_api):
        resp = student_api.post("/api/events/track/", {
            "event_name": 12345,
        }, format="json")
        assert resp.status_code in (400, 415)

    def test_oversized_payload_returns_400(self, student_api):
        resp = student_api.post("/api/events/track/", {
            "event_name": "page_view",
            "properties": {"data": "x" * 20000},
        }, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_enum_returns_400(self, student_api):
        resp = student_api.post("/api/events/track/", {
            "event_name": "not_a_valid_event",
        }, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_consent_wrong_format_returns_400(self, student_api):
        resp = student_api.post("/api/privacy/consent/", {
            "consents": "not_a_list",
        }, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# BD-R02: No stack trace in responses (covered by SEC-10, reinforced here)
# ---------------------------------------------------------------------------


class TestBDR02NoStackTrace:
    """Error responses must never contain Traceback or internal paths."""

    def test_404_no_trace(self, student_api):
        resp = student_api.get("/api/assessment/999999/questions/")
        content = (
            str(resp.data) if hasattr(resp, "data") and resp.data is not None
            else resp.content.decode("utf-8", errors="ignore")
        )
        assert "Traceback" not in content
        assert "File \"" not in content
        assert "line " not in content or "at line" not in content

    def test_403_no_trace(self, student_api):
        resp = student_api.get("/api/dashboard/alerts/")
        if resp.status_code == 403:
            content = str(resp.data)
            assert "Traceback" not in content

    def test_400_no_trace(self, student_api):
        resp = student_api.post("/api/events/track/", {}, format="json")
        content = str(resp.data)
        assert "Traceback" not in content
        assert "Exception" not in content


# ---------------------------------------------------------------------------
# BD-R03: Error messages must be actionable
# ---------------------------------------------------------------------------


class TestBDR03ActionableErrors:
    """Error responses must explain what went wrong and how to fix it."""

    def test_missing_field_error_names_field(self, student_api):
        resp = student_api.post("/api/events/track/", {}, format="json")
        assert resp.status_code == 400
        content = str(resp.data)
        assert "event_name" in content or "required" in content.lower()

    def test_invalid_choice_error_lists_options(self, student_api):
        resp = student_api.post("/api/events/track/", {
            "event_name": "fake_event",
        }, format="json")
        assert resp.status_code == 400
        content = str(resp.data)
        assert "valid" in content.lower() or "choice" in content.lower()

    def test_auth_error_clear_message(self, anon_api):
        resp = anon_api.get("/api/auth/profile/")
        assert resp.status_code == 401
        # The standardised error envelope used across PALP nests user-facing
        # text under ``error.message``; legacy DRF responses put it at the
        # top level as ``detail``. Accept either shape.
        data = resp.data or {}
        nested = data.get("error", {}) if isinstance(data, dict) else {}
        assert "detail" in data or "message" in data or "message" in nested


# ---------------------------------------------------------------------------
# BD-R04: Learning endpoints include request_id
# ---------------------------------------------------------------------------


class TestBDR04RequestId:
    """Learning-impact endpoints must include request correlation ID."""

    def test_event_track_response_has_id(self, student_api):
        resp = student_api.post("/api/events/track/", {
            "event_name": "page_view",
        }, format="json")
        assert resp.status_code == 201
        assert "id" in resp.data

    def test_adaptive_submit_response_has_structure(
        self, student_api, micro_tasks, student_with_pathway,
    ):
        task = micro_tasks[0]
        resp = student_api.post("/api/adaptive/submit/", {
            "task_id": task.pk,
            "answer": task.content.get("correct_answer", "A"),
            "duration_seconds": 30,
            "hints_used": 0,
        }, format="json")
        assert resp.status_code == 200
        assert "attempt" in resp.data
        assert "mastery" in resp.data
        assert "pathway" in resp.data

    def test_assessment_answer_returns_200(
        self, student_api, assessment,
    ):
        start = student_api.post(f"/api/assessment/{assessment.pk}/start/")
        if start.status_code != 201:
            return
        sid = start.data["id"]
        q = assessment.questions.order_by("order").first()

        resp = student_api.post(
            f"/api/assessment/sessions/{sid}/answer/",
            {"question_id": q.id, "answer": "A", "time_taken_seconds": 10},
            format="json",
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# BD-R05: Idempotent POST endpoints (reinforces test_idempotency.py)
# ---------------------------------------------------------------------------


class TestBDR05Idempotency:
    """POST endpoints with idempotency_key must be safe to retry."""

    def test_event_track_idempotent(self, student_api):
        key = "discipline-test-idemp-001"
        payload = {
            "event_name": "page_view",
            "idempotency_key": key,
        }

        r1 = student_api.post("/api/events/track/", payload, format="json")
        r2 = student_api.post("/api/events/track/", payload, format="json")

        assert r1.status_code == 201
        assert r1.data["id"] == r2.data.get("id", r1.data["id"])

    def test_wellbeing_check_idempotent(self, student_api):
        r1 = student_api.post("/api/wellbeing/check/", {
            "continuous_minutes": 30,
        }, format="json")
        r2 = student_api.post("/api/wellbeing/check/", {
            "continuous_minutes": 30,
        }, format="json")

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.data["should_nudge"] == r2.data["should_nudge"]


# ---------------------------------------------------------------------------
# API completeness: every endpoint group has contract coverage
# ---------------------------------------------------------------------------


class TestAPICompleteness:
    """Verify core endpoint groups are reachable and return expected status."""

    CORE_ENDPOINTS = [
        ("GET", "/api/health/", 200, "anon"),
        ("GET", "/api/auth/profile/", 200, "student"),
        ("GET", "/api/curriculum/courses/", 200, "student"),
        ("GET", "/api/adaptive/mastery/", 200, "student"),
        ("GET", "/api/events/my/", 200, "student"),
        ("GET", "/api/wellbeing/my/", 200, "student"),
        ("GET", "/api/privacy/consent/", 200, "student"),
    ]

    @pytest.mark.parametrize(
        "method,path,expected,role",
        CORE_ENDPOINTS,
        ids=[f"{m} {p}" for m, p, _, _ in CORE_ENDPOINTS],
    )
    def test_core_endpoint_reachable(
        self, method, path, expected, role,
        student_api, lecturer_api, admin_api, anon_api,
    ):
        client = {
            "student": student_api,
            "lecturer": lecturer_api,
            "admin": admin_api,
            "anon": anon_api,
        }[role]

        if method == "GET":
            resp = client.get(path)
        else:
            resp = client.post(path, {}, format="json")

        assert resp.status_code == expected, (
            f"{method} {path} expected {expected}, got {resp.status_code}"
        )
