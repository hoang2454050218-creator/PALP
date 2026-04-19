"""Canary token helper.

Embed a per-request hex token in the system prompt; verify the LLM
response does NOT contain the token. A leaked canary indicates the
model echoed the system prompt back — either the prompt isn't being
respected (bad config) or the user injected something that pulled the
prompt out (worst case). Both cases must refuse + alert.

Pure stdlib so no extra dependency. The store is module-level
process-local; in a multi-worker prod the canary should ride with the
request id (which is what the orchestrator does — it stores the
canary inside the audit log row so the postmortem can correlate).
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass


@dataclass
class Canary:
    token: str
    placeholder: str  # how it appears in the prompt

    def is_leaked_in(self, response: str) -> bool:
        return bool(response) and self.token in response


def make_canary() -> Canary:
    token = secrets.token_hex(8)
    placeholder = f"[INTERNAL_TOKEN={token}]"
    return Canary(token=token, placeholder=placeholder)
