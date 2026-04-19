"""Affect engine tests — pure-NumPy, no DB needed."""
from __future__ import annotations

import pytest

from affect.engines.keystroke import estimate as estimate_keystroke
from affect.engines.linguistic import estimate as estimate_linguistic


class TestKeystrokeEngine:
    def test_insufficient_sample_returns_low_confidence(self):
        snap = estimate_keystroke({"inter_key_intervals_ms": [120, 130]})
        assert snap.label == "insufficient_sample"
        assert snap.confidence < 1.0

    def test_high_backspace_marks_frustrated(self):
        snap = estimate_keystroke({
            "inter_key_intervals_ms": [200] * 30 + [3500] * 8,
            "backspace_ratio": 0.5,
            "burst_count": 0,
            "pause_count": 8,
        })
        assert snap.label in {"frustrated", "stressed", "negative"}
        assert snap.valence <= 0

    def test_engaged_pattern(self):
        snap = estimate_keystroke({
            "inter_key_intervals_ms": [60] * 80,
            "backspace_ratio": 0.02,
            "burst_count": 80,
            "pause_count": 0,
        })
        assert snap.label == "engaged"
        assert snap.arousal > 0.5

    def test_disengaged_pattern(self):
        snap = estimate_keystroke({
            "inter_key_intervals_ms": [800] * 30 + [4000] * 10,
            "backspace_ratio": 0.05,
            "burst_count": 1,
            "pause_count": 12,
        })
        assert snap.label in {"disengaged", "neutral"}


class TestLinguisticEngine:
    def test_positive_vi(self):
        snap = estimate_linguistic("Mình thấy hiểu rồi và rất tự tin khi giải bài này")
        assert snap.valence > 0.3
        assert snap.label == "positive"

    def test_frustrated_vi(self):
        snap = estimate_linguistic("Mình bực mình quá, không hiểu gì cả!!!")
        assert snap.valence < -0.3
        assert snap.label in {"frustrated", "negative"}

    def test_negation_flips_valence(self):
        normal = estimate_linguistic("Mình thấy vui vẻ với bài học này")
        negated = estimate_linguistic("Mình không thấy vui vẻ với bài học này")
        assert negated.valence <= normal.valence

    def test_short_text_returns_insufficient(self):
        snap = estimate_linguistic("ok")
        assert snap.label == "insufficient_sample"

    def test_english_path_works(self):
        snap = estimate_linguistic("I am so confused and frustrated", language="en")
        assert snap.valence < -0.3
