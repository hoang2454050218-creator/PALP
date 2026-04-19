"""Anonymous percentile benchmark within a same-ability cohort.

The whole point of this module is **safety**:

* Never expose ranks ("you are #7"), names, or absolute scores of others.
* Bucket into wide bands so a single low number doesn't humiliate.
* Flip the framing for the bottom 25% — show "in the building phase"
  copy with peer-success examples, not "below 75% of your cohort".
* Refuse to compute when the cohort is too small (cell suppression).
* Refuse to compute when the student has not opted in.

Any caller relying on this service must already check
``has_consent(user, "peer_comparison")``; the middleware does that for
the HTTP layer but background tasks must do it explicitly.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from django.conf import settings


@dataclass
class BenchmarkResult:
    available: bool
    reason: str = ""
    cohort_size: int = 0
    band: str = ""
    safe_copy: str = ""
    encouragement: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Wide bands intentionally — narrower bands become rank-like quickly.
_BAND_TOP = "top_25_pct"
_BAND_ABOVE = "above_median"
_BAND_BELOW = "below_median"
_BAND_BUILDING = "building_phase"


_COPY = {
    _BAND_TOP: (
        "Bạn đang trong nhóm tiến nhanh nhất của cohort cùng xuất phát "
        "điểm. Tiếp tục giữ nhịp — có thể thử dạy lại concept để củng cố."
    ),
    _BAND_ABOVE: (
        "Bạn đang ổn trong cohort cùng xuất phát điểm. Tập trung vào "
        "1-2 concept yếu hơn để rút ngắn khoảng còn lại."
    ),
    _BAND_BELOW: (
        "Bạn đang trong nửa dưới của cohort. Đây là điểm khởi đầu — "
        "không phải đích đến. Hãy chọn concept yếu nhất để bắt đầu."
    ),
    _BAND_BUILDING: (
        "Bạn đang trong giai đoạn xây nền tảng. Trong cohort cùng xuất "
        "phát điểm, có nhiều bạn từng ở vị trí của bạn 4 tuần trước, "
        "hiện đã thông thạo concept tiếp theo. Có muốn xem cách họ học?"
    ),
}


def _band_for(percentile: float) -> str:
    if percentile >= 75:
        return _BAND_TOP
    if percentile >= 50:
        return _BAND_ABOVE
    if percentile >= 25:
        return _BAND_BELOW
    return _BAND_BUILDING


def _percentile_of(score: float, cohort_scores: list[float]) -> float:
    if not cohort_scores:
        return 0.0
    below = sum(1 for s in cohort_scores if s < score)
    equal = sum(1 for s in cohort_scores if abs(s - score) < 1e-9)
    n = len(cohort_scores)
    # Standard "midrank" percentile -- fair to ties.
    return (below + 0.5 * equal) / n * 100.0


def compute_benchmark(student) -> BenchmarkResult:
    """Return the student's anonymous percentile band within their cohort."""
    from peer.models import PeerCohort

    cohort = (
        PeerCohort.objects
        .filter(student_class__memberships__student=student, is_active=True)
        .filter(members=student)
        .order_by("-created_at")
        .first()
    )

    if not cohort:
        return BenchmarkResult(
            available=False,
            reason="cohort_not_assigned",
            safe_copy=(
                "Bạn chưa được gán vào cohort nào. Hệ thống cần ít nhất 4 "
                "tuần dữ liệu để xếp cohort cùng năng lực."
            ),
        )

    minimum = int(settings.PALP_PEER["COHORT_MIN_SIZE"])
    if cohort.members_count < minimum:
        return BenchmarkResult(
            available=False,
            reason="cohort_too_small",
            cohort_size=cohort.members_count,
            safe_copy=(
                "Cohort của bạn còn nhỏ — hệ thống không hiển thị so sánh "
                "khi cohort dưới 10 người để bảo vệ riêng tư."
            ),
        )

    own_score = _composite_mastery(student)
    cohort_scores = [
        _composite_mastery(member)
        for member in cohort.members.all()
    ]
    percentile = _percentile_of(own_score, cohort_scores)
    band = _band_for(percentile)

    return BenchmarkResult(
        available=True,
        cohort_size=cohort.members_count,
        band=band,
        safe_copy=_COPY[band],
        encouragement=_encouragement_for(band),
    )


def _composite_mastery(student) -> float:
    """Average mastery across active concepts. Robust to missing concepts."""
    from adaptive.models import MasteryState

    values = list(
        MasteryState.objects
        .filter(student=student)
        .values_list("p_mastery", flat=True)
    )
    if not values:
        return 0.0
    return sum(values) / len(values)


def _encouragement_for(band: str) -> str:
    if band == _BAND_BUILDING:
        return "growth_invitation"
    if band == _BAND_BELOW:
        return "next_step_focus"
    if band == _BAND_ABOVE:
        return "consolidation"
    return "teach_back"
