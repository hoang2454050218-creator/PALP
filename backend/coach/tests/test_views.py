"""HTTP integration tests for the Coach views."""
from __future__ import annotations

import pytest

from coach.models import CoachConsent, CoachConversation
from privacy.constants import CONSENT_VERSION
from privacy.models import ConsentRecord


pytestmark = pytest.mark.django_db


def _grant(student, *purposes):
    for p in purposes:
        ConsentRecord.objects.create(
            user=student, purpose=p, granted=True, version=CONSENT_VERSION,
        )


class TestCoachConsentEndpoint:
    def test_default_get_creates_row(self, student_api):
        resp = student_api.get("/api/coach/consent/")
        assert resp.status_code == 200
        assert resp.data["ai_coach_local"] is True
        assert resp.data["ai_coach_cloud"] is False

    def test_patch_records_consent_version(self, student_api, student):
        resp = student_api.patch(
            "/api/coach/consent/",
            {"ai_coach_cloud": True},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["ai_coach_cloud"] is True
        assert ConsentRecord.objects.filter(
            user=student, purpose="ai_coach_cloud", granted=True,
        ).exists()


class TestCoachMessageEndpoint:
    def test_message_blocked_without_consent(self, student_api, student):
        consent, _ = CoachConsent.objects.get_or_create(student=student)
        # Even though the model defaults ai_coach_local=True the privacy
        # ConsentRecord doesn't exist yet -> middleware returns 403.
        resp = student_api.post(
            "/api/coach/message/", {"text": "Hi"}, format="json",
        )
        assert resp.status_code == 403

    def test_message_allowed_with_consent(self, student_api, student):
        _grant(student, "ai_coach_local")
        resp = student_api.post(
            "/api/coach/message/",
            {"text": "Giải thích cho mình định luật Hooke."},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["assistant_turn"]["role"] == "assistant"
        assert resp.data["emergency_triggered"] is False

    def test_empty_text_is_400(self, student_api, student):
        _grant(student, "ai_coach_local")
        resp = student_api.post(
            "/api/coach/message/", {"text": " "}, format="json",
        )
        assert resp.status_code == 400


class TestCoachConversationViews:
    def test_list_returns_only_owner_conversations(
        self, student_api, lecturer_api, student, student_b,
    ):
        # student creates a conversation
        CoachConversation.objects.create(student=student)
        CoachConversation.objects.create(student=student_b)

        resp = student_api.get("/api/coach/conversations/")
        assert resp.status_code == 200
        assert len(resp.data["conversations"]) == 1

    def test_lecturer_cannot_list_student_conversations(self, lecturer_api):
        resp = lecturer_api.get("/api/coach/conversations/")
        assert resp.status_code == 403

    def test_end_conversation(self, student_api, student):
        conv = CoachConversation.objects.create(student=student)
        resp = student_api.post(f"/api/coach/conversations/{conv.id}/end/")
        assert resp.status_code == 200
        assert resp.data["status"] == "ended"
