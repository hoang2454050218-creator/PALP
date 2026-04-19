"""Tool registry tests — RBAC + read-only contract."""
from __future__ import annotations

import pytest

from adaptive.models import MasteryState
from coach.tools import registry as tool_registry


pytestmark = pytest.mark.django_db


class TestExecute:
    def test_unknown_tool_rejected(self, student):
        result = tool_registry.execute("update_mastery", {}, student)
        assert result["error"] == "tool_not_allowed"

    def test_invalid_args_rejected(self, student):
        result = tool_registry.execute("get_mastery", "not a dict", student)
        assert result["error"] == "invalid_args"

    def test_rbac_blocks_other_student(self, student, student_b):
        result = tool_registry.execute(
            "get_mastery", {"student_id": student_b.id}, student,
        )
        assert result["error"] == "rbac_denied"

    def test_get_mastery_returns_owner_data(self, student, concepts):
        MasteryState.objects.create(
            student=student, concept=concepts[0], p_mastery=0.6,
        )
        result = tool_registry.execute("get_mastery", {}, student)
        assert "result" in result
        names = [c["concept_name"] for c in result["result"]["concepts"]]
        assert concepts[0].name in names

    def test_get_pathway_returns_none_when_missing(self, student):
        result = tool_registry.execute("get_pathway", {}, student)
        assert result["result"]["pathway"] is None
