"""Counterfactual generator — "if you fixed X, your score would shift by Y".

For the additive risk score we can compute exact counterfactuals: if
the student raises their academic dimension from 0.30 to 0.55, the
composite drops by ``(0.55 - 0.30) * weight_academic * 100``.

We rank counterfactuals by *expected_delta* but also tag a
``feasibility`` (0..1) so the UI can prefer scenarios the student can
actually act on (e.g. behavioral change is more feasible than
academic-history change).
"""
from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings


@dataclass
class Counterfactual:
    feature_key: str
    current_value: float
    target_value: float
    expected_delta: float
    feasibility: float
    actionable_hint: str


_FEASIBILITY = {
    "academic": 0.30,        # historical, slow to move
    "behavioral": 0.85,      # focus / idle / tabs — student controls today
    "engagement": 0.75,      # login cadence, micro-task completion
    "psychological": 0.60,   # frustration / give-ups (peer + coach can help)
    "metacognitive": 0.65,   # confidence calibration improves with reflection
}

_ACTIONABLE = {
    "academic": (
        "Khoảng cách so với mặt bằng tiến độ là điều cần thời gian. Mỗi tuần "
        "ưu tiên 2 concept yếu nhất sẽ rút ngắn dần."
    ),
    "behavioral": (
        "Tuần này thử block 25 phút tập trung không tab khác (Pomodoro). "
        "Sensing layer sẽ ghi nhận và composite sẽ giảm rõ."
    ),
    "engagement": (
        "Đăng nhập đều đặn 5 ngày/tuần (mỗi lần 20 phút) đã đủ để engagement "
        "đẩy composite xuống đáng kể."
    ),
    "psychological": (
        "Khi gặp give-up, đặt lại bài về mức dễ hơn rồi quay lại. Coach có "
        "thể giúp nếu bạn nhắn 'mình đang nản'."
    ),
    "metacognitive": (
        "Trước khi nộp, dành 5 giây ước lượng confidence. Calibration tốt "
        "lên giúp bạn biết khi nào cần xem worked example."
    ),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_for_risk(snapshot, *, target_composite: float | None = None) -> list[Counterfactual]:
    """Return counterfactuals that would lower the composite by `target_delta`.

    The default target is "drop composite by 10 points". For each
    dimension we compute the change in raw value needed and the
    feasibility tag.
    """
    weights = dict(getattr(settings, "PALP_RISK_WEIGHTS", {}))
    composite = float(getattr(snapshot, "composite", 0.0))
    if target_composite is None:
        target_composite = max(0.0, composite - 10.0)
    needed_delta = composite - float(target_composite)
    if needed_delta <= 0:
        return []

    out: list[Counterfactual] = []
    for key, weight in weights.items():
        raw = float(snapshot.dimensions.get(key, 0.5))
        weight = float(weight)
        if weight <= 0:
            continue

        # delta in dimension space to achieve `needed_delta` points
        # using only this dimension (in 0..1 space).
        dim_change = needed_delta / (weight * 100.0)
        target_dim = max(0.0, min(1.0, raw - dim_change))
        actual_change = raw - target_dim

        if actual_change <= 0.001:
            continue

        out.append(
            Counterfactual(
                feature_key=key,
                current_value=round(raw, 4),
                target_value=round(target_dim, 4),
                expected_delta=round(-actual_change * weight * 100.0, 4),
                feasibility=_FEASIBILITY.get(key, 0.5),
                actionable_hint=_ACTIONABLE.get(key, ""),
            )
        )

    # Rank by combined "feasibility * |expected_delta|" so the most
    # actionable wins (not the largest possible drop on paper).
    out.sort(
        key=lambda c: -(c.feasibility * abs(c.expected_delta))
    )
    return out
