"""Tests for intent classifier + LLM router."""
from __future__ import annotations

import pytest

from coach.llm import intent as intent_mod
from coach.llm import router as router_mod
from privacy.constants import CONSENT_VERSION
from privacy.models import ConsentRecord


pytestmark = pytest.mark.django_db


class TestClassify:
    def test_explain_concept(self):
        result = intent_mod.classify("Giải thích cho mình định luật Hooke.")
        assert result.intent == "explain_concept"
        assert result.is_sensitive is False

    def test_self_harm_wins_over_homework(self):
        text = "Mình muốn chết. Nhưng cũng cần làm bài tập 1, 2, 3."
        result = intent_mod.classify(text)
        assert result.intent == "self_harm"
        assert result.is_sensitive is True

    def test_empty_text_returns_small_talk(self):
        result = intent_mod.classify("")
        assert result.intent == "small_talk"

    def test_no_diacritics_frustration_still_detected(self):
        # Vietnamese students often type without accents (no IME, mobile,
        # code editor). The router must still send frustration to local.
        result = intent_mod.classify("Minh buc qua, hoc mai khong vao")
        assert result.is_sensitive is True
        assert result.intent in {"frustration", "give_up", "stress"}

    def test_no_diacritics_give_up_still_detected(self):
        result = intent_mod.classify("muon bo cuoc qua roi")
        assert result.is_sensitive is True
        assert result.intent == "give_up"

    def test_no_diacritics_self_harm_still_detected(self):
        # Worst-case: a student in distress typing without accents
        # MUST still trigger the sensitive path.
        result = intent_mod.classify("minh khong muon song nua")
        assert result.is_sensitive is True
        assert result.intent in {"self_harm", "suicidal_ideation"}

    def test_diacritics_still_work(self):
        result = intent_mod.classify("mình bực quá, muốn bỏ cuộc")
        assert result.is_sensitive is True
        assert result.intent in {"frustration", "give_up"}


class TestRouter:
    def _grant(self, user, *purposes):
        for p in purposes:
            ConsentRecord.objects.create(
                user=user, purpose=p, granted=True, version=CONSENT_VERSION,
            )

    def test_sensitive_intent_routes_local(self, student):
        self._grant(student, "ai_coach_cloud")  # even with cloud consent
        decision = router_mod.route(
            intent="self_harm", user=student, daily_token_usage=0,
        )
        assert decision.target == "local"
        assert decision.reason == "sensitive_intent"

    def test_no_cloud_consent_routes_local(self, student):
        decision = router_mod.route(
            intent="explain_concept", user=student, daily_token_usage=0,
        )
        assert decision.target == "local"
        assert decision.reason == "no_cloud_consent"

    def test_budget_exceeded_routes_local(self, student, settings):
        self._grant(student, "ai_coach_cloud")
        settings.PALP_COACH = {**settings.PALP_COACH, "DAILY_TOKEN_LIMIT_PER_USER": 100}
        decision = router_mod.route(
            intent="explain_concept", user=student, daily_token_usage=200,
        )
        assert decision.target == "local"
        assert decision.reason == "budget_exceeded"

    def test_default_routes_cloud(self, student):
        self._grant(student, "ai_coach_cloud")
        decision = router_mod.route(
            intent="explain_concept", user=student, daily_token_usage=0,
        )
        assert decision.target == "cloud"
        assert decision.reason == "default"
