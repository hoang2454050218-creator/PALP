"""Prompt-injection / jailbreak heuristic scanner.

Pure-Python pattern bank — no external model. Faster than the
DistilBERT classifier described in the playbook and good enough for the
first ship; the classifier is added in Phase 4B once we have labelled
data. Output severity drives the orchestrator to either pass-through,
sanitise, or refuse.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from django.conf import settings


INJECTION_PATTERNS: list[str] = [
    # English direct override
    r"ignore (previous|prior|all|above)",
    r"disregard (previous|prior|all|above)",
    r"forget (everything|all|previous|your)",
    # Role confusion
    r"you are now (a|an)",
    r"act as (a|an)",
    r"pretend (to be|you are)",
    r"system\s*[:|>]",
    r"(human|user|assistant)\s*[:|>]",
    # Format injection markers
    r"```system",
    r"<\|system\|>",
    r"\[\[system\]\]",
    # Jailbreak markers
    r"\bDAN\s*mode\b",
    r"developer mode",
    r"\bjailbreak\b",
    r"\bunrestricted\b",
    # Vietnamese variants
    r"bỏ qua (hướng dẫn|chỉ thị|prompt|tất cả)",
    r"đóng vai (là|một)",
    r"giả vờ (là|làm)",
]


@dataclass
class InjectionScanResult:
    severity: str  # "clean" | "suspicious" | "blocked"
    findings: list[dict]
    sanitized_text: str


_COMPILED = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def scan(text: str) -> InjectionScanResult:
    """Scan ``text`` for prompt-injection / jailbreak patterns."""
    if not text:
        return InjectionScanResult(severity="clean", findings=[], sanitized_text=text)

    findings: list[dict] = []
    sanitized = text

    for pattern in _COMPILED:
        for match in pattern.finditer(text):
            findings.append({
                "pattern": pattern.pattern,
                "match": match.group(),
                "severity": "suspicious",
            })
            # Strip the matched span — replace with a placeholder so
            # the cleaned text still parses naturally.
            sanitized = sanitized.replace(match.group(), "[REDACTED]")

    max_input = int(
        getattr(settings, "PALP_COACH", {}).get("MAX_INPUT_LENGTH", 4000)
    )
    if len(text) > max_input:
        findings.append({
            "pattern": "excessive_length",
            "match": f"len={len(text)}",
            "severity": "suspicious",
        })
        sanitized = sanitized[:max_input]

    if text.count("\n") > 50:
        findings.append({
            "pattern": "many_newlines",
            "match": f"newlines={text.count(chr(10))}",
            "severity": "suspicious",
        })

    if not findings:
        return InjectionScanResult(severity="clean", findings=[], sanitized_text=text)

    severity = "blocked" if len(findings) >= 3 else "suspicious"
    return InjectionScanResult(
        severity=severity,
        findings=findings,
        sanitized_text=sanitized,
    )
