"""Instructor co-pilot service layer.

Two deterministic, template-based generators ship today — that's
deliberate so output stays auditable + free of hallucination. A real
LLM-backed generator can drop in later behind the same interface
(see ``coach.llm.client.LLMClient``).

* **generate_exercise** — picks a template per (concept, difficulty)
  and fills it with the concept's metadata. Always lecturer-reviewed.
* **draft_feedback** — composes a structured weekly summary from
  signals + risk + reflection rows.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable

from django.db import transaction
from django.utils import timezone

from instructor_copilot.models import FeedbackDraft, GeneratedExercise


# ---------------------------------------------------------------------------
# Exercise generation
# ---------------------------------------------------------------------------

EXERCISE_TEMPLATES: dict[str, dict] = {
    "concept_check_easy": {
        "title": "Kiểm tra khái niệm: {concept_name}",
        "question": (
            "Phát biểu nào sau đây mô tả đúng nhất về '{concept_name}' "
            "trong môn {course_name}?"
        ),
        "options": [
            "Đây là khái niệm cốt lõi cần nắm trước khi sang bước tiếp.",
            "Khái niệm này không bắt buộc.",
            "Khái niệm này chỉ áp dụng cho bài tập nâng cao.",
            "Khái niệm này chỉ là ký hiệu / convention.",
        ],
        "correct_answer": "Đây là khái niệm cốt lõi cần nắm trước khi sang bước tiếp.",
        "explanation": (
            "Concept '{concept_name}' là tiền đề cho các concept sau trong "
            "đồ thị kiến thức của môn {course_name}."
        ),
        "hints": [
            "Hãy nghĩ về ngữ cảnh xuất hiện của concept này trong giáo trình.",
            "Concept càng ở gốc đồ thị càng có nhiều concept phụ thuộc.",
        ],
    },
    "application_medium": {
        "title": "Áp dụng: {concept_name}",
        "question": (
            "Trong tình huống thực tế của môn {course_name}, bạn áp dụng "
            "concept '{concept_name}' như thế nào để giải quyết bài toán?"
        ),
        "options": [
            "Xác định dữ kiện → mô hình hoá → áp dụng concept → kiểm tra kết quả.",
            "Áp dụng ngay không cần mô hình hoá.",
            "Concept này không dùng cho bài toán thực tế.",
            "Chỉ dùng concept này khi đã biết đáp án.",
        ],
        "correct_answer": "Xác định dữ kiện → mô hình hoá → áp dụng concept → kiểm tra kết quả.",
        "explanation": (
            "Quy trình 4 bước này là pattern chuẩn khi áp dụng '{concept_name}' "
            "vào bài toán mới. Việc kiểm tra cuối là bước nhiều sinh viên hay bỏ qua."
        ),
        "hints": [
            "Bắt đầu từ việc liệt kê dữ kiện đã biết.",
            "Mô hình hoá thường là phần khó nhất — đừng vội bỏ qua.",
        ],
    },
    "synthesis_hard": {
        "title": "Tổng hợp: {concept_name}",
        "question": (
            "So sánh '{concept_name}' với một concept khác trong môn "
            "{course_name} mà bạn cho là gần nghĩa. Điểm khác biệt cốt lõi?"
        ),
        "options": [
            "Khác nhau ở phạm vi áp dụng và giả thiết đầu vào.",
            "Hai concept hoàn toàn giống nhau.",
            "Không có concept nào tương tự.",
            "Chỉ khác nhau ở tên gọi.",
        ],
        "correct_answer": "Khác nhau ở phạm vi áp dụng và giả thiết đầu vào.",
        "explanation": (
            "Hai concept gần nghĩa thường có overlap về toán học nhưng giả "
            "thiết đầu vào (boundary conditions) khác nhau. Đây là ý quan "
            "trọng cho bài thi tổng hợp."
        ),
        "hints": [
            "Hãy nghĩ tới các điều kiện biên / giả thiết.",
            "Thử áp dụng cho 2 ví dụ cụ thể để thấy khác biệt.",
        ],
    },
}

_DIFFICULTY_TO_TEMPLATE = {
    GeneratedExercise.Difficulty.EASY: "concept_check_easy",
    GeneratedExercise.Difficulty.MEDIUM: "application_medium",
    GeneratedExercise.Difficulty.HARD: "synthesis_hard",
}


@transaction.atomic
def generate_exercise(*, concept, course, requested_by, difficulty: int) -> GeneratedExercise:
    template_key = _DIFFICULTY_TO_TEMPLATE.get(
        difficulty, "concept_check_easy"
    )
    template = EXERCISE_TEMPLATES[template_key]
    ctx = {
        "concept_name": concept.name,
        "course_name": course.name,
    }
    title = template["title"].format(**ctx)
    body = {
        "question": template["question"].format(**ctx),
        "options": template["options"],
        "correct_answer": template["correct_answer"],
        "explanation": template["explanation"].format(**ctx),
        "hints": template["hints"],
    }
    return GeneratedExercise.objects.create(
        course=course,
        concept=concept,
        requested_by=requested_by,
        template_key=template_key,
        difficulty=difficulty,
        title=title,
        body=body,
    )


@transaction.atomic
def approve_exercise(*, exercise: GeneratedExercise, reviewer, notes: str = "") -> GeneratedExercise:
    """Promote a draft into a real curriculum.MicroTask."""
    from curriculum.models import MicroTask, Milestone

    milestone = (
        Milestone.objects
        .filter(course=exercise.course, concepts=exercise.concept)
        .order_by("order")
        .first()
    )
    if milestone is None:
        raise ValueError(
            "No milestone owns this concept — create one before approving."
        )

    micro_task = MicroTask.objects.create(
        milestone=milestone,
        concept=exercise.concept,
        title=exercise.title,
        difficulty=exercise.difficulty,
        estimated_minutes=5 + 5 * int(exercise.difficulty),
        is_active=True,
        content=exercise.body,
    )
    exercise.status = GeneratedExercise.Status.PUBLISHED
    exercise.published_micro_task_id = micro_task.id
    exercise.review_notes = (exercise.review_notes + "\n" + notes).strip()
    exercise.save(
        update_fields=[
            "status", "published_micro_task_id", "review_notes", "updated_at",
        ]
    )
    return exercise


# ---------------------------------------------------------------------------
# Feedback drafting
# ---------------------------------------------------------------------------

@dataclass
class FeedbackComputed:
    summary: str
    highlights: list[str]
    concerns: list[str]
    suggestions: list[str]


@transaction.atomic
def draft_feedback(*, student, requested_by, week_start) -> FeedbackDraft:
    """Compose a weekly feedback draft from existing signals + risk."""
    computed = _compute_feedback(student, week_start=week_start)
    draft, _ = FeedbackDraft.objects.update_or_create(
        student=student,
        week_start=week_start,
        requested_by=requested_by,
        defaults={
            "summary": computed.summary,
            "highlights": computed.highlights,
            "concerns": computed.concerns,
            "suggestions": computed.suggestions,
        },
    )
    return draft


def _compute_feedback(student, *, week_start) -> FeedbackComputed:
    from risk.scoring import compute_risk_score
    from signals.models import SignalSession

    snapshot = compute_risk_score(student, persist=False)

    week_end = week_start + timedelta(days=7)
    signal_rows = SignalSession.objects.filter(
        student=student,
        window_start__date__gte=week_start,
        window_start__date__lt=week_end,
    )
    total_focus = round(sum(r.focus_minutes for r in signal_rows), 1)
    total_give_ups = sum(r.give_up_count for r in signal_rows)
    distinct_days = len({r.window_start.date() for r in signal_rows})

    highlights = _highlights(snapshot, total_focus, distinct_days)
    concerns = _concerns(snapshot, total_give_ups, distinct_days)
    suggestions = _suggestions(snapshot, total_focus, distinct_days)

    summary = (
        f"Tuần {week_start.isoformat()}: composite risk {snapshot.composite:.0f}/100. "
        f"Tập trung {total_focus} phút, {distinct_days} ngày học, "
        f"{total_give_ups} lần give-up."
    )
    return FeedbackComputed(
        summary=summary,
        highlights=highlights,
        concerns=concerns,
        suggestions=suggestions,
    )


def _highlights(snapshot, total_focus: float, distinct_days: int) -> list[str]:
    out: list[str] = []
    if total_focus >= 240:
        out.append(f"Đã tập trung {total_focus:.0f} phút — vượt ngưỡng healthy 240'.")
    if distinct_days >= 5:
        out.append(f"Học đều {distinct_days}/7 ngày — pattern tốt cho retention.")
    for key, val in snapshot.dimensions.items():
        if val < 0.30:  # low risk = strong dimension
            out.append(f"Dimension '{key}' đang rất tốt (risk {val:.2f}).")
    return out[:5]


def _concerns(snapshot, total_give_ups: int, distinct_days: int) -> list[str]:
    out: list[str] = []
    if total_give_ups >= 3:
        out.append(f"{total_give_ups} lần give-up — có thể đang vượt ZPD.")
    if distinct_days <= 2:
        out.append(f"Chỉ học {distinct_days}/7 ngày — engagement thấp.")
    for key, val in snapshot.dimensions.items():
        if val >= 0.65:  # high risk
            out.append(f"Dimension '{key}' đang ở mức cảnh báo (risk {val:.2f}).")
    return out[:5]


def _suggestions(snapshot, total_focus: float, distinct_days: int) -> list[str]:
    out: list[str] = []
    if total_focus < 180:
        out.append("Đặt mục tiêu tập trung 180 phút tuần sau (3 buổi × 60').")
    if distinct_days <= 3:
        out.append("Thử nhịp '5 ngày học, 2 ngày nghỉ' để đỡ overload.")

    severity = _severity_for(snapshot)
    if severity == "red":
        out.append(
            "Đề xuất 1-1 30' với GV để diagnose root-cause và lập kế hoạch."
        )
    elif severity == "yellow":
        out.append(
            "Gửi 1 nudge nhẹ trong tuần — đừng chờ tới lúc thành red."
        )
    return out[:5]


def _severity_for(snapshot) -> str:
    """Resolve severity for both ``RiskBreakdown`` (dataclass) and ``RiskScore`` (model)."""
    explicit = getattr(snapshot, "severity", None)
    if isinstance(explicit, str):
        return explicit

    from django.conf import settings as dj_settings

    thresholds = getattr(dj_settings, "PALP_RISK_THRESHOLDS", {})
    composite = float(getattr(snapshot, "composite", 0.0))
    if composite >= float(thresholds.get("ALERT_RED", 70.0)):
        return "red"
    if composite >= float(thresholds.get("ALERT_YELLOW", 50.0)):
        return "yellow"
    return "green"


def _ensure_iterable(values) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        return [values]
    if isinstance(values, Iterable):
        return list(values)
    return [str(values)]
