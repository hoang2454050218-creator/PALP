"""Detector unit tests."""
from __future__ import annotations

import pytest

from emergency.detector import detect


class TestDetect:
    def test_critical_self_harm(self):
        result = detect("Tôi muốn tự tử.")
        assert result.triggered is True
        assert result.severity == "critical"
        assert any("tự tử" in k for k in result.matched_keywords)

    def test_high_hopelessness(self):
        result = detect("Cảm thấy không còn ý nghĩa, tuyệt vọng.")
        assert result.triggered is True
        assert result.severity == "high"

    def test_medium_burnout(self):
        result = detect("Mình muốn bỏ học vì stress nặng.")
        assert result.triggered is True
        assert result.severity == "medium"

    def test_clean_text(self):
        result = detect("Hôm nay học bài rất vui.")
        assert result.triggered is False
        assert result.severity == ""
