"""Refusal templates and triggers.

Centralised so the orchestrator never inlines copy. Each refusal has:

* ``trigger_kind`` — short machine-readable code that goes into the audit log.
* ``template`` — the user-facing Vietnamese copy.

The orchestrator picks a trigger via :func:`choose_refusal`. If no
trigger matches the input is treated as "safe to send to LLM".
"""
from __future__ import annotations

import re
from dataclasses import dataclass


REFUSAL_TEMPLATES: dict[str, str] = {
    "academic_dishonesty": (
        "Mình không thể viết bài thay bạn — đó không tôn trọng việc học của bạn. "
        "Nhưng mình có thể giúp brainstorm outline, review draft, hoặc giải thích "
        "concept. Bạn muốn cách nào?"
    ),
    "grade_manipulation": (
        "Mình không thể giúp việc đó. Nếu bạn lo lắng về điểm, mình có thể giúp "
        "lên kế hoạch cải thiện được không?"
    ),
    "other_student_pii": (
        "Mình không chia sẻ thông tin của bạn khác. Mỗi sinh viên có privacy "
        "riêng. Mình có thể giúp gì khác cho bạn?"
    ),
    "out_of_scope_advice": (
        "Đây không phải lĩnh vực mình có thể tư vấn an toàn. Hãy tham vấn chuyên "
        "gia phù hợp. Trong khi đó, mình giúp việc học nhé?"
    ),
    "inappropriate_content": (
        "Cuộc trò chuyện này không phù hợp. Mình ở đây để hỗ trợ học tập. Bạn "
        "cần giúp gì về bài?"
    ),
    "jailbreak": (
        "Xin lỗi, mình không thể trả lời theo cách bạn yêu cầu. Mình ở đây để "
        "hỗ trợ học tập. Bạn cần giúp gì về bài học?"
    ),
    "injection_blocked": (
        "Tin nhắn của bạn có vẻ chứa hướng dẫn không an toàn cho mình. Bạn có "
        "thể nói lại bằng câu hỏi tự nhiên hơn được không?"
    ),
    "cooldown_active": (
        "Coach đang tạm khoá cho tài khoản của bạn. Vui lòng thử lại sau hoặc "
        "liên hệ giảng viên nếu cần hỗ trợ."
    ),
    "consent_missing": (
        "Bạn cần bật quyền 'Trợ lý AI nội bộ' trong Quyền riêng tư trước khi "
        "chat với coach."
    ),
    "rate_limit": (
        "Bạn đã đạt giới hạn token hôm nay. Coach sẽ sẵn sàng lại vào ngày mai."
    ),
}


@dataclass
class RefusalDecision:
    triggered: bool
    kind: str = ""
    response: str = ""


# Patterns are kept intentionally short — heavy NLU is reserved for the
# (optional) intent classifier. We only intercept clear, unambiguous
# "the user is asking for the wrong thing" cases here.
_PATTERNS: list[tuple[str, str]] = [
    # Vietnamese "write the essay for me" — must contain a clear
    # academic-work noun (bài / essay / luận văn / đề tài / bài tập)
    # between the verb (viết/làm/giải) and the recipient marker
    # (giúp/cho/thay/hộ). Without the noun, "giải thích cho mình"
    # would false-positive on every legitimate explanation request.
    (
        "academic_dishonesty",
        r"(viết|làm|giải)\s+"
        r"(?:\w+\s+){0,2}"
        r"(bài(?:\s+tập)?|essay|luận văn|luận án|đề tài|báo cáo|tiểu luận)"
        r"\s+(?:\w+\s+){0,2}"
        r"(giúp|cho|thay|hộ)\s+(mình|tôi|em|t)\b",
    ),
    (
        "academic_dishonesty",
        r"(write|do|complete)\s+(my|the)\s+(essay|homework|assignment|paper)\s+for\s+me",
    ),
    (
        "grade_manipulation",
        r"(sửa|nâng|tăng|đổi|chỉnh)\s+(điểm|kết quả|grade)",
    ),
    (
        "other_student_pii",
        r"(cho|nói|báo|gửi)\s+(mình|tôi|em)\s+(?:biết\s+)?(?:điểm|email|sđt|số điện thoại|thông tin)\s+(của|của bạn)\s+\w+",
    ),
    (
        "out_of_scope_advice",
        r"(thuốc|chữa|chẩn đoán|bệnh|luật|đầu tư|cổ phiếu)\s+(gì|nào|cho|tôi|mình)",
    ),
    (
        "inappropriate_content",
        r"(sex|porn|18\+|nude)",
    ),
]
_COMPILED = [(k, re.compile(p, re.IGNORECASE)) for k, p in _PATTERNS]


def choose_refusal(text: str) -> RefusalDecision:
    """Return a refusal if any rule matches; otherwise allow the LLM to handle it."""
    if not text:
        return RefusalDecision(triggered=False)
    for kind, pattern in _COMPILED:
        if pattern.search(text):
            return RefusalDecision(
                triggered=True,
                kind=kind,
                response=REFUSAL_TEMPLATES.get(kind, REFUSAL_TEMPLATES["jailbreak"]),
            )
    return RefusalDecision(triggered=False)


def refuse(kind: str) -> str:
    """Look up the canonical refusal template for ``kind``."""
    return REFUSAL_TEMPLATES.get(kind, REFUSAL_TEMPLATES["jailbreak"])
