"""Emergency Pipeline view tests."""
from __future__ import annotations

import pytest

from emergency.detector import DetectionResult
from emergency.services import escalate


pytestmark = pytest.mark.django_db


def _detection():
    return DetectionResult(
        triggered=True, severity="critical",
        matched_keywords=["tự tử"], score=0.95,
    )


class TestQueueView:
    def test_lecturer_sees_own_queue(
        self, lecturer_api, class_with_members, student, lecturer,
    ):
        escalate(student=student, detection=_detection())
        resp = lecturer_api.get("/api/emergency/queue/")
        assert resp.status_code == 200
        assert len(resp.data["entries"]) == 1
        assert resp.data["entries"][0]["event"]["severity"] == "critical"

    def test_student_cannot_view_queue(self, student_api):
        resp = student_api.get("/api/emergency/queue/")
        assert resp.status_code == 403


class TestEventDetailView:
    def test_acknowledge_changes_state(
        self, lecturer_api, class_with_members, student, lecturer,
    ):
        event = escalate(student=student, detection=_detection())
        resp = lecturer_api.post(
            f"/api/emergency/events/{event.id}/acknowledge/",
            {"notes": "đã liên hệ"}, format="json",
        )
        assert resp.status_code == 200
        assert resp.data["status"] == "acknowledged"

    def test_other_lecturer_blocked(
        self,
        lecturer_other_api,
        class_with_members,
        student,
    ):
        event = escalate(student=student, detection=_detection())
        resp = lecturer_other_api.get(f"/api/emergency/events/{event.id}/")
        assert resp.status_code == 403


class TestContactView:
    def test_get_returns_none_when_missing(self, student_api):
        resp = student_api.get("/api/emergency/contact/")
        assert resp.status_code == 200
        assert resp.data["contact"] is None

    def test_patch_records_consent_timestamp(self, student_api, student):
        resp = student_api.patch(
            "/api/emergency/contact/",
            {
                "name": "Mẹ Lan",
                "phone": "0901234567",
                "relationship": "parent",
                "consent_given": True,
            },
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["consent_given"] is True
        assert resp.data["consent_given_at"] is not None
