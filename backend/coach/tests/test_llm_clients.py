"""Tests for the OpenAI-compatible + Ollama LLM clients.

We never call the real network — every test patches ``httpx.Client``
to return a canned response. That keeps the suite fast (sub-second)
and means the suite passes without any API key configured.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from coach.llm.client import LLMRequest
from coach.llm.ollama_client import OllamaClient
from coach.llm.openai_compat import LLMTransportError, OpenAICompatClient


def _request() -> LLMRequest:
    return LLMRequest(
        system_prompt="bạn là coach",
        user_message="giải thích ứng suất chính",
        intent="explain_concept",
        user_id=42,
    )


def _mock_httpx(*, status_code: int, payload: dict):
    """Return a context-manager mock that ``httpx.Client(...)`` becomes.

    We patch ``httpx.Client`` (not the module-level ``post``) because
    both clients use the ``with httpx.Client(...) as client`` idiom.
    """
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    response.text = str(payload)

    client_mock = MagicMock()
    client_mock.post.return_value = response

    cm = MagicMock()
    cm.__enter__.return_value = client_mock
    cm.__exit__.return_value = False
    return cm


# ---------------------------------------------------------------------------
# OpenAICompatClient
# ---------------------------------------------------------------------------

class TestOpenAICompatClient:
    def test_refuses_when_api_key_missing(self):
        client = OpenAICompatClient(api_key="", model="claude-sonnet-4-6")
        with pytest.raises(LLMTransportError) as exc:
            client.generate(_request())
        assert "api_key is empty" in str(exc.value)

    def test_happy_path_extracts_text(self):
        cm = _mock_httpx(
            status_code=200,
            payload={
                "id": "chatcmpl-abc",
                "choices": [
                    {
                        "message": {"content": "Ứng suất chính là..."},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 50, "completion_tokens": 30},
            },
        )
        client = OpenAICompatClient(
            api_key="sk-fake", base_url="https://api.example.test/v1",
            model="claude-sonnet-4-6",
        )
        with patch("httpx.Client", return_value=cm):
            response = client.generate(_request())

        assert response.text == "Ứng suất chính là..."
        assert response.tokens_in == 50
        assert response.tokens_out == 30
        assert response.model == "claude-sonnet-4-6"
        assert response.raw["finish_reason"] == "stop"

    def test_4xx_raises_transport_error(self):
        cm = _mock_httpx(status_code=401, payload={"error": "invalid_api_key"})
        client = OpenAICompatClient(api_key="sk-fake", model="claude-sonnet-4-6")
        with patch("httpx.Client", return_value=cm):
            with pytest.raises(LLMTransportError) as exc:
                client.generate(_request())
        assert "HTTP 401" in str(exc.value)

    def test_malformed_response_raises_transport_error(self):
        cm = _mock_httpx(status_code=200, payload={"choices": []})
        client = OpenAICompatClient(api_key="sk-fake", model="claude-sonnet-4-6")
        with patch("httpx.Client", return_value=cm):
            with pytest.raises(LLMTransportError) as exc:
                client.generate(_request())
        assert "Malformed" in str(exc.value)

    def test_falls_back_to_token_estimate_when_usage_missing(self):
        cm = _mock_httpx(
            status_code=200,
            payload={
                "choices": [{"message": {"content": "ngắn"}, "finish_reason": "stop"}],
            },
        )
        client = OpenAICompatClient(api_key="sk-fake", model="any")
        with patch("httpx.Client", return_value=cm):
            response = client.generate(_request())
        assert response.tokens_in > 0
        assert response.tokens_out > 0

    def test_extra_headers_forwarded(self):
        cm = _mock_httpx(
            status_code=200,
            payload={
                "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
            },
        )
        client = OpenAICompatClient(
            api_key="sk-fake", model="any",
            extra_headers={"HTTP-Referer": "https://palp.local"},
        )
        with patch("httpx.Client", return_value=cm) as client_factory:
            client.generate(_request())
        call = cm.__enter__.return_value.post.call_args
        assert call.kwargs["headers"]["HTTP-Referer"] == "https://palp.local"
        assert call.kwargs["headers"]["Authorization"].startswith("Bearer ")


# ---------------------------------------------------------------------------
# OllamaClient
# ---------------------------------------------------------------------------

class TestOllamaClient:
    def test_happy_path(self):
        cm = _mock_httpx(
            status_code=200,
            payload={
                "model": "qwen2.5:7b",
                "message": {"role": "assistant", "content": "Mình có thể giúp bạn..."},
                "prompt_eval_count": 80,
                "eval_count": 22,
                "done_reason": "stop",
                "eval_duration": 12345678,
            },
        )
        client = OllamaClient(model="qwen2.5:7b")
        with patch("httpx.Client", return_value=cm):
            response = client.generate(_request())
        assert response.text == "Mình có thể giúp bạn..."
        assert response.provider == "ollama"
        assert response.tokens_in == 80
        assert response.tokens_out == 22
        assert response.raw["done_reason"] == "stop"

    def test_5xx_raises_transport_error(self):
        cm = _mock_httpx(status_code=500, payload={"error": "model unavailable"})
        client = OllamaClient(model="qwen2.5:7b")
        with patch("httpx.Client", return_value=cm):
            with pytest.raises(LLMTransportError):
                client.generate(_request())

    def test_connection_refused_falls_through_as_transport_error(self):
        client = OllamaClient(model="qwen2.5:7b", base_url="http://127.0.0.1:1")
        with pytest.raises(LLMTransportError):
            client.generate(_request())


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProviderFactory:
    def test_default_falls_back_to_echo_when_key_missing(self, settings):
        settings.PALP_COACH = {
            **settings.PALP_COACH,
            "DEFAULT_PROVIDER": "openai_compat",
            "OPENAI_COMPAT": {**settings.PALP_COACH["OPENAI_COMPAT"], "API_KEY": ""},
        }
        from coach.llm.client import get_default_client

        client = get_default_client()
        assert client.provider == "echo"

    def test_default_returns_real_client_when_key_present(self, settings):
        settings.PALP_COACH = {
            **settings.PALP_COACH,
            "DEFAULT_PROVIDER": "openai_compat",
            "OPENAI_COMPAT": {
                **settings.PALP_COACH["OPENAI_COMPAT"],
                "API_KEY": "sk-fake",
                "MODEL": "claude-sonnet-4-6",
            },
        }
        from coach.llm.client import get_default_client

        client = get_default_client()
        assert client.provider == "openai_compat"
        assert client.model == "claude-sonnet-4-6"

    def test_router_falls_back_to_echo_on_factory_error(self, settings, student):
        # Grant cloud consent so the router actually picks the cloud
        # client; the factory will then fail (empty API key) and the
        # router must downgrade to Echo without raising.
        from privacy.constants import CONSENT_VERSION
        from privacy.models import ConsentRecord

        ConsentRecord.objects.create(
            user=student, purpose="ai_coach_cloud", granted=True,
            version=CONSENT_VERSION,
        )
        settings.PALP_COACH = {
            **settings.PALP_COACH,
            "CLOUD_PROVIDER": "openai_compat",
            "LOCAL_PROVIDER": "echo",
            "OPENAI_COMPAT": {**settings.PALP_COACH["OPENAI_COMPAT"], "API_KEY": ""},
        }
        from coach.llm.router import route

        decision = route(intent="explain_concept", user=student, daily_token_usage=0)
        assert decision.target == "cloud"
        assert decision.client.provider == "echo"

    def test_ollama_factory_does_not_call_network(self, settings):
        from coach.llm.client import _make_ollama

        client = _make_ollama()
        assert client.provider == "ollama"
        assert client.base_url == "http://localhost:11434"
