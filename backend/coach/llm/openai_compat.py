"""OpenAI-compatible LLM client.

One client class, many providers. Works with:

* **OpenAI** directly (``base_url=https://api.openai.com/v1``).
* **key4u.shop** (Vietnamese aggregator that proxies Claude / GPT /
  Gemini through an OpenAI-compatible endpoint).
* **OpenRouter** (``base_url=https://openrouter.ai/api/v1``).
* **Azure OpenAI** with the standard ``/v1`` shim.
* Any **vLLM**, **LocalAI**, **Ollama** (Ollama also exposes an
  OpenAI-compatible surface at ``/v1`` from version 0.1.14).

That breadth is the whole reason we picked this abstraction over a
provider-specific SDK: the operator can hot-swap providers by
changing two env vars (``BASE_URL`` and ``MODEL``) without touching
code or re-deploying.

Safety properties:

* The client NEVER logs the request body or headers — only model
  name + token counts + latency. The ``PIIScrubLogFilter`` adds a
  second scrubbing layer in ``privacy/middleware.py`` for any leak.
* On any vendor-side error (timeout, 5xx, malformed response) we
  raise ``LLMTransportError`` so the orchestrator can fall back to
  the local client and the conversation never crashes.
* The ``api_key`` is read fresh from settings on every instantiation
  so rotating the key in ``.env`` and sending SIGHUP / restarting
  the worker is enough — no key ever sits in module-level state.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from coach.llm.client import LLMRequest, LLMResponse, _estimate_tokens

logger = logging.getLogger("palp.coach.llm")


class LLMTransportError(RuntimeError):
    """Raised when the upstream provider fails (network, 5xx, bad JSON)."""


@dataclass
class OpenAICompatClient:
    """OpenAI Chat Completions compatible client.

    Parameters mirror the OpenAI Python SDK so swapping in the real
    SDK later is a one-line change.
    """

    api_key: str
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    provider: str = "openai_compat"
    timeout_seconds: float = 30.0
    max_output_tokens: int = 1024
    temperature: float = 0.4
    extra_headers: dict | None = None

    def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise LLMTransportError(
                f"{self.provider}: api_key is empty — refusing to call upstream."
            )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_message},
            ],
            "max_tokens": self.max_output_tokens,
            "temperature": self.temperature,
        }

        start = time.perf_counter()
        try:
            data = self._post_chat_completions(payload)
        except Exception as exc:
            elapsed = int((time.perf_counter() - start) * 1000)
            logger.warning(
                "LLM upstream failed: provider=%s model=%s latency_ms=%d",
                self.provider, self.model, elapsed,
            )
            raise LLMTransportError(str(exc)) from exc

        elapsed = int((time.perf_counter() - start) * 1000)
        text = self._extract_text(data)
        usage = data.get("usage", {}) or {}
        tokens_in = int(usage.get("prompt_tokens") or 0) or _estimate_tokens(
            request.system_prompt + request.user_message,
        )
        tokens_out = int(usage.get("completion_tokens") or 0) or _estimate_tokens(text)

        logger.info(
            "LLM call ok: provider=%s model=%s tokens_in=%d tokens_out=%d latency_ms=%d",
            self.provider, self.model, tokens_in, tokens_out, elapsed,
        )

        return LLMResponse(
            text=text,
            provider=self.provider,
            model=self.model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=max(elapsed, 1),
            raw={"id": data.get("id"), "finish_reason": self._finish_reason(data)},
        )

    def _post_chat_completions(self, payload: dict) -> dict:
        """Defer the import so the Django startup never depends on httpx.

        We keep the network call thin + sync because the orchestrator
        is itself sync (Django REST). Async fan-out can come later if
        we ever batch coach calls.
        """
        import httpx

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.extra_headers:
            headers.update(self.extra_headers)

        url = self.base_url.rstrip("/") + "/chat/completions"
        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.post(url, headers=headers, json=payload)
        if resp.status_code >= 400:
            raise LLMTransportError(
                f"HTTP {resp.status_code}: {resp.text[:200]}",
            )
        return resp.json()

    @staticmethod
    def _extract_text(data: dict) -> str:
        try:
            return (
                data["choices"][0]["message"]["content"]
                or ""
            ).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMTransportError(f"Malformed response: {exc}") from exc

    @staticmethod
    def _finish_reason(data: dict) -> str:
        try:
            return str(data["choices"][0].get("finish_reason") or "")
        except (KeyError, IndexError, TypeError):
            return ""
