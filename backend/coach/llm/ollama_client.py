"""Ollama local LLM client.

Talks to a locally-running Ollama daemon (default
``http://localhost:11434``). Models we recommend:

* ``qwen2.5:7b``  — best Vietnamese coverage in 7B class
* ``llama3.2:3b`` — faster, smaller, weaker VN
* ``llama3.1:8b`` — strong English, decent VN

Why a separate Ollama client even though Ollama also exposes an
OpenAI-compatible surface at ``/v1``: the native ``/api/chat``
endpoint exposes useful fields (``eval_count``, ``eval_duration``,
``done_reason``) that the OpenAI shim drops. We use those for the
``LLMResponse.raw`` audit so on-call engineers can debug local LLM
slow paths without scraping container logs.

If Ollama is not installed / not running, ``generate`` raises
``LLMTransportError`` and the orchestrator falls back to the safe
``EchoClient``. Tests do this explicitly.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from coach.llm.client import LLMRequest, LLMResponse, _estimate_tokens
from coach.llm.openai_compat import LLMTransportError

logger = logging.getLogger("palp.coach.llm")


@dataclass
class OllamaClient:
    base_url: str = "http://localhost:11434"
    model: str = "qwen2.5:7b"
    provider: str = "ollama"
    timeout_seconds: float = 60.0
    temperature: float = 0.4
    num_predict: int = 1024

    def generate(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_message},
            ],
            "options": {
                "temperature": self.temperature,
                "num_predict": self.num_predict,
            },
        }

        start = time.perf_counter()
        try:
            data = self._post_chat(payload)
        except Exception as exc:
            elapsed = int((time.perf_counter() - start) * 1000)
            logger.warning(
                "Ollama upstream failed: model=%s latency_ms=%d",
                self.model, elapsed,
            )
            raise LLMTransportError(str(exc)) from exc

        elapsed = int((time.perf_counter() - start) * 1000)
        text = ((data.get("message") or {}).get("content") or "").strip()
        tokens_in = int(data.get("prompt_eval_count") or 0) or _estimate_tokens(
            request.system_prompt + request.user_message,
        )
        tokens_out = int(data.get("eval_count") or 0) or _estimate_tokens(text)

        logger.info(
            "Ollama call ok: model=%s tokens_in=%d tokens_out=%d latency_ms=%d",
            self.model, tokens_in, tokens_out, elapsed,
        )

        return LLMResponse(
            text=text,
            provider=self.provider,
            model=self.model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=max(elapsed, 1),
            raw={
                "done_reason": data.get("done_reason"),
                "eval_duration_ns": data.get("eval_duration"),
            },
        )

    def _post_chat(self, payload: dict) -> dict:
        import httpx

        url = self.base_url.rstrip("/") + "/api/chat"
        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.post(url, json=payload)
        if resp.status_code >= 400:
            raise LLMTransportError(
                f"Ollama HTTP {resp.status_code}: {resp.text[:200]}",
            )
        return resp.json()
