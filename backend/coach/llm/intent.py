"""Lightweight intent classifier.

Rule-based for now — the playbook calls for a distilled classifier in
Phase 4B but the rule-based version is good enough for the routing
decision (sensitive vs not) and shipping faster matters more than the
last 5 % accuracy. The set of intents matches the labels in the
playbook so a future ML classifier can drop in without changing
downstream consumers.

Vietnamese-without-diacritics handling: Vietnamese students very often
type without accents (no IME, mobile keyboard, code editor, …). We
match the user message against BOTH the original text and a
diacritic-stripped copy, so ``"buc qua, muon bo cuoc"`` triggers
``frustration`` + ``give_up`` exactly like the diacriticked form.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


def _strip_diacritics(text: str) -> str:
    """Decompose then drop combining marks.

    Safe for regex patterns too — NFKD never touches ASCII punctuation,
    so ``(tự (tử|sát|vẫn)|...)`` becomes ``(tu (tu|sat|van)|...)`` with
    the regex structure intact.
    """
    nfkd = unicodedata.normalize("NFKD", text)
    no_marks = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Vietnamese ``đ`` / ``Đ`` are not handled by NFKD diacritic
    # decomposition; map manually so "đồng" → "dong".
    return no_marks.replace("đ", "d").replace("Đ", "D")


SENSITIVE_INTENTS = frozenset({
    "frustration",
    "give_up",
    "stress",
    "wellbeing",
    "mental_health",
    "personal_struggle",
    "family",
    "self_harm",
    "suicidal_ideation",
})

INTENT_LABELS = (
    "explain_concept",
    "homework_help",
    "summary_request",
    "navigation_help",
    "feedback_request",
    "frustration",
    "give_up",
    "stress",
    "wellbeing",
    "mental_health",
    "personal_struggle",
    "family",
    "self_harm",
    "suicidal_ideation",
    "small_talk",
)


# Map keyword groups to intent labels. Vietnamese-first; English as
# fallback for code-switching.
_RULES: list[tuple[str, str]] = [
    ("self_harm", r"(tự (tử|sát|vẫn)|tự tổn thương|self[- ]harm|kill myself|end (it|my life)|muốn chết)"),
    ("suicidal_ideation", r"(không muốn sống|không có lý do để sống|suicidal|nghĩ đến cái chết)"),
    ("give_up", r"(bỏ học|drop out|bỏ cuộc|từ bỏ|không học nữa|nghỉ học)"),
    ("frustration", r"(bực|tức|chán nản|giận|frustrated|fed up)"),
    ("stress", r"(stress|căng thẳng|áp lực|kiệt sức|burnout|quá tải)"),
    ("wellbeing", r"(mệt|mất ngủ|ngủ không ngon|mất ngủ|sleep|cảm xúc)"),
    ("personal_struggle", r"(buồn|cô đơn|không ai hiểu|lonely|sad)"),
    ("family", r"(gia đình|bố mẹ|cha mẹ|family|parents)"),
    ("homework_help", r"(làm bài|bài tập|homework|exercise|hint|gợi ý cho bài|task)"),
    ("explain_concept", r"(giải thích|explain|hiểu|nghĩa là|là gì|what is|công thức|định nghĩa|định lý)"),
    ("summary_request", r"(tóm tắt|summary|tổng hợp|recap|key points)"),
    ("navigation_help", r"(làm sao để|how do i|where can i|tìm ở đâu|tab nào|màn hình)"),
    ("feedback_request", r"(feedback|nhận xét|review|đánh giá bài)"),
]
_COMPILED = [
    (
        label,
        re.compile(p, re.IGNORECASE),
        re.compile(_strip_diacritics(p), re.IGNORECASE),
    )
    for label, p in _RULES
]


@dataclass
class IntentResult:
    intent: str
    is_sensitive: bool
    confidence: float
    matched_pattern: str = ""


def classify(text: str) -> IntentResult:
    """Return the most-sensitive matching intent.

    Sensitivity wins over count — a single self_harm match beats five
    homework_help matches. This implements the playbook rule "route to
    the most sensitive intent when multi-intent".
    """
    if not text:
        return IntentResult(intent="small_talk", is_sensitive=False, confidence=0.0)

    text_no_diacritics = _strip_diacritics(text)
    matches: list[tuple[str, str]] = []
    for label, pattern_orig, pattern_strip in _COMPILED:
        m = pattern_orig.search(text)
        if m is None:
            m = pattern_strip.search(text_no_diacritics)
        if m:
            matches.append((label, m.group()))

    if not matches:
        return IntentResult(
            intent="small_talk",
            is_sensitive=False,
            confidence=0.0,
        )

    # Prefer sensitive matches; otherwise pick the first match (which
    # is the highest-priority rule per the order above).
    sensitive_matches = [m for m in matches if m[0] in SENSITIVE_INTENTS]
    if sensitive_matches:
        label, matched = sensitive_matches[0]
    else:
        label, matched = matches[0]

    return IntentResult(
        intent=label,
        is_sensitive=label in SENSITIVE_INTENTS,
        confidence=0.7,  # rule-based, not probabilistic — keep honest constant
        matched_pattern=matched,
    )
