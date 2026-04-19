"""LLM routing — decide cloud vs local for each request.

Decision tree (matches the playbook):

1. Sensitive intent (frustration / wellbeing / self-harm / …) → local LLM
2. No ``ai_coach_cloud`` consent → local LLM
3. Token budget exceeded for the day → local LLM (silent fallback)
4. Default → cloud LLM

Today both "cloud" and "local" map to the same Echo provider since
neither vendor is wired up in this drop. The router still records the
*decision* so the audit log shows the routing intent — when a real
provider lands, only the registry entry needs to change.
"""
from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from coach.llm.client import (
    LLMClient,
    PROVIDER_REGISTRY,
    EchoClient,
    get_default_client,
)
from coach.llm.intent import SENSITIVE_INTENTS


@dataclass
class RouteDecision:
    target: str  # "cloud" | "local"
    reason: str
    client: LLMClient
    consent_used: str  # "ai_coach_cloud" | "ai_coach_local"


def route(*, intent: str, user, daily_token_usage: int) -> RouteDecision:
    """Pick a client + record why."""
    palp_coach = getattr(settings, "PALP_COACH", {})
    daily_limit = int(palp_coach.get("DAILY_TOKEN_LIMIT_PER_USER", 50_000))

    # Sensitive intents always stay local — never leave the infra.
    if intent in SENSITIVE_INTENTS:
        return RouteDecision(
            target="local",
            reason="sensitive_intent",
            client=_resolve("LOCAL_PROVIDER"),
            consent_used="ai_coach_local",
        )

    cloud_consent = _has_consent(user, "ai_coach_cloud")
    if not cloud_consent:
        return RouteDecision(
            target="local",
            reason="no_cloud_consent",
            client=_resolve("LOCAL_PROVIDER"),
            consent_used="ai_coach_local",
        )

    if daily_token_usage >= daily_limit:
        return RouteDecision(
            target="local",
            reason="budget_exceeded",
            client=_resolve("LOCAL_PROVIDER"),
            consent_used="ai_coach_local",
        )

    return RouteDecision(
        target="cloud",
        reason="default",
        client=_resolve("CLOUD_PROVIDER"),
        consent_used="ai_coach_cloud",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve(setting_key: str) -> LLMClient:
    """Resolve the configured client; never crash on misconfig.

    Three failure modes are silently downgraded to ``EchoClient``:

    1. The provider name is missing from ``PROVIDER_REGISTRY``.
    2. The factory raises (e.g. missing API key for ``openai_compat``).
    3. Settings has no ``PALP_COACH`` block at all (test-only edge).

    The reasoning is the same as in ``client.get_default_client``:
    the chat flow must complete, never error. If the real provider
    fails *during* generation that's handled in ``coach/services.py``
    by catching ``LLMTransportError`` and retrying with the local
    fallback client.
    """
    palp_coach = getattr(settings, "PALP_COACH", {})
    name = palp_coach.get(setting_key) or palp_coach.get("DEFAULT_PROVIDER", "echo")
    factory = PROVIDER_REGISTRY.get(name)
    if factory is None:
        return get_default_client()
    try:
        return factory()
    except Exception:  # noqa: BLE001
        return get_default_client()


def _has_consent(user, purpose: str) -> bool:
    try:
        from privacy.services import has_consent

        return has_consent(user, purpose)
    except Exception:
        return False
