"""PII Guard tests — mask + restore + idempotence."""
from __future__ import annotations

import pytest

from coach.security import pii_guard


pytestmark = pytest.mark.django_db


class TestMask:
    def test_mask_email(self):
        result = pii_guard.mask("Liên hệ tôi qua test@example.com nhé.")
        assert "test@example.com" not in result.text
        assert "[EMAIL_0]" in result.text
        assert result.mapping["[EMAIL_0]"] == "test@example.com"

    def test_mask_phone(self):
        result = pii_guard.mask("Số của tôi là 0901234567.")
        assert "0901234567" not in result.text
        assert any(t.startswith("[PHONE_") for t in result.mapping)

    def test_mask_student_id(self):
        result = pii_guard.mask("MSSV của em là 22020123.")
        assert "22020123" not in result.text
        assert any(t.startswith("[STUDENT_ID_") for t in result.mapping)

    def test_mask_returns_count(self):
        result = pii_guard.mask("a@b.com và 0901234567")
        assert result.count >= 2

    def test_no_pii_returns_text_unchanged(self):
        result = pii_guard.mask("Bài này khó quá.")
        assert result.text == "Bài này khó quá."
        assert result.mapping == {}


class TestRestore:
    def test_restore_round_trips(self):
        original = "Email tôi là test@example.com và sđt 0901234567."
        masked = pii_guard.mask(original)
        restored = pii_guard.restore(masked.text, masked.mapping)
        assert restored == original

    def test_restore_with_empty_mapping_is_noop(self):
        assert pii_guard.restore("Hello", {}) == "Hello"
