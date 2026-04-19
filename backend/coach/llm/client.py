"""LLM client abstraction.

Defines a common protocol shared by the cloud and local clients plus
two safe defaults (``EchoClient`` and ``MockClient``) that never call
out to a vendor. Real Anthropic / OpenAI / Ollama clients can be added
in a follow-up commit by implementing :class:`LLMClient` and
registering them in :data:`PROVIDER_REGISTRY`.

The default provider — set via ``settings.PALP_COACH["DEFAULT_PROVIDER"]``
— ships as ``"echo"`` so the system works out of the box without any
API key. Tests use ``MockClient`` directly via dependency injection.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Iterable, Protocol


@dataclass
class LLMRequest:
    system_prompt: str
    user_message: str
    canary_placeholder: str = ""
    intent: str = ""
    user_id: int | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    raw: dict = field(default_factory=dict)


class LLMClient(Protocol):
    """Protocol the orchestrator depends on. Real clients implement ``generate``."""

    provider: str
    model: str

    def generate(self, request: LLMRequest) -> LLMResponse:  # pragma: no cover - protocol
        ...


# ---------------------------------------------------------------------------
# Built-in providers
# ---------------------------------------------------------------------------

class EchoClient:
    """Default safe client used when no real provider is configured.

    Returns a deterministic, friendly Vietnamese response that
    acknowledges the user message. Good for browser demos and unit
    tests; never reaches out to the network.
    """

    provider = "echo"
    model = "echo-1"

    def generate(self, request: LLMRequest) -> LLMResponse:
        start = time.perf_counter()
        intent = request.intent or "general"
        text = self._compose(request.user_message, intent)
        elapsed = int((time.perf_counter() - start) * 1000)
        return LLMResponse(
            text=text,
            provider=self.provider,
            model=self.model,
            tokens_in=_estimate_tokens(request.system_prompt + request.user_message),
            tokens_out=_estimate_tokens(text),
            latency_ms=max(elapsed, 1),
        )

    @staticmethod
    def _compose(user_message: str, intent: str) -> str:
        if intent == "explain_concept":
            return (
                "Mình hiểu bạn muốn được giải thích thêm. Đây là câu trả lời gợi "
                "ý dựa trên kiến thức nội bộ — hãy đối chiếu với tài liệu khoá "
                "học để chắc chắn. Nếu cần ví dụ cụ thể hơn, cứ bảo mình."
            )
        if intent == "homework_help":
            return (
                "Mình có thể giúp bạn từng bước, không giải hộ cả bài. Bắt đầu "
                "bằng việc bạn nói cho mình biết bạn đang vướng ở bước nào nhé."
            )
        if intent == "summary_request":
            return (
                "Mình sẽ tóm tắt các ý chính ngắn gọn ngay sau khi bạn cho biết "
                "phần nào trong bài học bạn cần nhất."
            )
        if intent == "navigation_help":
            return (
                "Bạn có thể tìm tính năng đó trong sidebar bên trái. Mình có thể "
                "chỉ chính xác hơn nếu bạn nói cụ thể đang muốn làm gì."
            )
        if intent == "feedback_request":
            return (
                "Mình sẽ nhận xét trên 3 trục: rõ ý / cấu trúc / dẫn chứng. Bạn "
                "gửi đoạn cần xem là mình bắt đầu được."
            )
        return (
            "Mình ghi nhận tin nhắn của bạn. Bạn có thể cho mình thêm ngữ cảnh "
            "để mình giúp tốt hơn được không?"
        )


@dataclass
class MockClient:
    """Test-friendly client whose response is fully controllable.

    Useful in unit tests:

    >>> client = MockClient(text="trả lời cố định", model="mock-1")
    """

    text: str = "Đây là phản hồi giả lập từ mock LLM."
    provider: str = "mock"
    model: str = "mock-1"
    raise_exc: Exception | None = None
    on_call: Callable[[LLMRequest], None] | None = None

    def generate(self, request: LLMRequest) -> LLMResponse:
        if self.on_call is not None:
            self.on_call(request)
        if self.raise_exc is not None:
            raise self.raise_exc
        return LLMResponse(
            text=self.text,
            provider=self.provider,
            model=self.model,
            tokens_in=_estimate_tokens(request.system_prompt + request.user_message),
            tokens_out=_estimate_tokens(self.text),
            latency_ms=1,
        )


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

def _make_openai_compat() -> "LLMClient":
    """Build the OpenAI-compatible client from settings.

    Reads ``PALP_COACH["OPENAI_COMPAT"]`` so operators can rotate the
    key by editing ``.env`` and restarting the worker — no code change
    needed. If the key is missing we deliberately raise so the router
    falls back to ``EchoClient`` instead of silently calling upstream
    with an empty Authorization header.
    """
    from django.conf import settings

    from coach.llm.openai_compat import OpenAICompatClient

    cfg = getattr(settings, "PALP_COACH", {}).get("OPENAI_COMPAT", {}) or {}
    api_key = cfg.get("API_KEY") or ""
    if not api_key:
        raise ValueError(
            "OpenAICompat client requested but PALP_COACH.OPENAI_COMPAT.API_KEY "
            "is empty. Set OPENAI_COMPAT_API_KEY in .env."
        )
    return OpenAICompatClient(
        api_key=api_key,
        base_url=cfg.get("BASE_URL") or "https://api.openai.com/v1",
        model=cfg.get("MODEL") or "gpt-4o-mini",
        provider=cfg.get("PROVIDER_LABEL") or "openai_compat",
        timeout_seconds=float(cfg.get("TIMEOUT_SECONDS") or 30.0),
        max_output_tokens=int(cfg.get("MAX_OUTPUT_TOKENS") or 1024),
        temperature=float(cfg.get("TEMPERATURE") or 0.4),
    )


def _make_ollama() -> "LLMClient":
    from django.conf import settings

    from coach.llm.ollama_client import OllamaClient

    cfg = getattr(settings, "PALP_COACH", {}).get("OLLAMA", {}) or {}
    return OllamaClient(
        base_url=cfg.get("BASE_URL") or "http://localhost:11434",
        model=cfg.get("MODEL") or "qwen2.5:7b",
        timeout_seconds=float(cfg.get("TIMEOUT_SECONDS") or 60.0),
        temperature=float(cfg.get("TEMPERATURE") or 0.4),
        num_predict=int(cfg.get("NUM_PREDICT") or 1024),
    )


PROVIDER_REGISTRY: dict[str, Callable[[], LLMClient]] = {
    "echo": EchoClient,
    "mock": MockClient,
    "openai_compat": _make_openai_compat,
    "ollama": _make_ollama,
}


def get_default_client() -> LLMClient:
    """Resolve the default LLMClient based on settings.

    Falls back to ``EchoClient`` if the configured provider isn't
    registered OR if the factory raises (typical: missing API key).
    We never crash here because a misconfigured env var shouldn't
    break the chat flow — the orchestrator can still answer safely
    with the echo template.
    """
    from django.conf import settings

    name = (
        getattr(settings, "PALP_COACH", {}).get("DEFAULT_PROVIDER", "echo")
        or "echo"
    )
    factory = PROVIDER_REGISTRY.get(name, EchoClient)
    try:
        return factory()
    except Exception:  # noqa: BLE001 — intentional: never crash the chat
        return EchoClient()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _estimate_tokens(text: str) -> int:
    """Quick token-count proxy. ~4 chars per token (English/Vietnamese mix)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def chunked_history(turns: Iterable, max_turns: int = 10) -> list:
    """Trim conversation history to the most recent ``max_turns`` turns."""
    out = list(turns)
    return out[-max_turns:]
