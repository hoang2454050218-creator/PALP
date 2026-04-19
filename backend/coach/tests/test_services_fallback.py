"""Verify the orchestrator gracefully falls back when the real LLM dies."""
from __future__ import annotations

import pytest

from coach.llm.client import LLMRequest, LLMResponse, MockClient
from coach.llm.openai_compat import LLMTransportError
from coach.models import CoachConsent
from coach.services import process_message
from privacy.constants import CONSENT_VERSION
from privacy.models import ConsentRecord


pytestmark = pytest.mark.django_db


def _grant_coach(user):
    CoachConsent.objects.update_or_create(
        student=user,
        defaults={
            "ai_coach_local": True,
            "ai_coach_cloud": False,
            "share_emergency_contact": False,
        },
    )
    ConsentRecord.objects.create(
        user=user, purpose="ai_coach_local", granted=True, version=CONSENT_VERSION,
    )


class FailingClient:
    provider = "openai_compat"
    model = "claude-sonnet-4-6"

    def generate(self, request: LLMRequest) -> LLMResponse:
        raise LLMTransportError("fake 503 from upstream")


class TestUpstreamFailureFallback:
    def test_falls_back_to_echo_and_marks_provider(self, student):
        _grant_coach(student)
        result = process_message(
            student=student,
            text="Giải thích định luật Hooke giúp mình",
            client=FailingClient(),
        )
        # Conversation must complete — student never sees an error.
        assert result.assistant_turn.content
        # Provider tag in the assistant turn shows the fallback happened.
        assert "fallback" in (result.assistant_turn.llm_provider or "")
        # Safety flags must record the upstream failure for ops.
        flags = result.safety_flags or []
        kinds = {f.get("kind") for f in flags}
        assert "llm_upstream_failed" in kinds

    def test_mock_client_still_works_when_no_failure(self, student):
        _grant_coach(student)
        result = process_message(
            student=student,
            text="Giải thích ứng suất tiếp",
            client=MockClient(text="Đây là câu trả lời mock cố định"),
        )
        assert "mock cố định" in result.assistant_turn.content
        assert not any(
            f.get("kind") == "llm_upstream_failed"
            for f in result.safety_flags or []
        )
