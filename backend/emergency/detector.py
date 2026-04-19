"""Emergency detection — keyword + heuristic severity classifier.

The playbook calls for a zero-shot LLM detector running in parallel
with the chat. We ship the deterministic rule-based version first
because:

* it is reliable in offline / no-vendor mode,
* it has zero per-message cost,
* its decisions are auditable line-by-line.

The interface mirrors the eventual ML-classifier so it can drop in
later.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


CRITICAL_PATTERNS = [
    r"tự (tử|sát|vẫn)",
    r"tự tổn thương",
    r"muốn chết",
    r"không muốn sống nữa",
    r"kết thúc cuộc đời",
    r"end (it|my life)",
    r"kill myself",
    r"suicide",
    r"self[- ]?harm",
]

HIGH_PATTERNS = [
    r"không còn ý nghĩa",
    r"không có lý do (để|sống)",
    r"tuyệt vọng",
    r"hopeless",
    r"can'?t take (it|this) anymore",
    r"không chịu nổi nữa",
    r"tôi không còn",
]

MEDIUM_PATTERNS = [
    r"bỏ học",
    r"drop out",
    r"không muốn học (nữa|tiếp)",
    r"stress nặng",
    r"burnt out",
    r"kiệt sức",
    r"depression",
    r"trầm cảm",
]


@dataclass
class DetectionResult:
    triggered: bool
    severity: str  # "" | "medium" | "high" | "critical"
    matched_keywords: list[str]
    score: float
    notes: str = ""


def detect(text: str) -> DetectionResult:
    """Scan a user message and return severity + matched keywords."""
    if not text:
        return DetectionResult(False, "", [], 0.0)

    lower = text.lower()
    matches: list[str] = []

    for level, patterns in (
        ("critical", CRITICAL_PATTERNS),
        ("high", HIGH_PATTERNS),
        ("medium", MEDIUM_PATTERNS),
    ):
        for pattern in patterns:
            for m in re.finditer(pattern, lower, flags=re.IGNORECASE):
                matches.append(m.group())
        if matches:
            score = _score_for(level, matches)
            return DetectionResult(
                triggered=True,
                severity=level,
                matched_keywords=matches,
                score=score,
                notes=f"pattern-detector:{level}",
            )

    return DetectionResult(False, "", [], 0.0)


def _score_for(level: str, matches: list) -> float:
    base = {"medium": 0.55, "high": 0.78, "critical": 0.95}[level]
    return min(1.0, base + 0.02 * (len(matches) - 1))
