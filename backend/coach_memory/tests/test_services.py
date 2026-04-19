"""Coach memory service + view tests."""
from __future__ import annotations

import pytest

from coach_memory.models import (
    EpisodicMemory,
    ProceduralMemory,
    SemanticMemory,
)
from coach_memory.services import (
    MemorySnapshot,
    recall,
    record_strategy_outcome,
    upsert_semantic,
    write_episodic,
)
from privacy.constants import CONSENT_VERSION
from privacy.models import ConsentRecord


pytestmark = pytest.mark.django_db


def _grant(user, *purposes):
    for p in purposes:
        ConsentRecord.objects.create(
            user=user, purpose=p, granted=True, version=CONSENT_VERSION,
        )


class TestWriteEpisodic:
    def test_creates_episode(self, student):
        ep = write_episodic(
            student=student, kind="struggle", summary="Vướng ở ứng suất chính",
            detail={"concept_id": 1}, salience=0.7,
        )
        assert isinstance(ep, EpisodicMemory)
        assert ep.kind == "struggle"
        assert ep.salience == 0.7

    def test_truncates_summary(self, student):
        long_summary = "x" * 500
        ep = write_episodic(
            student=student, kind="struggle", summary=long_summary,
        )
        assert len(ep.summary) <= 240


class TestUpsertSemantic:
    def test_creates_then_updates(self, student):
        a = upsert_semantic(
            student=student, key="career_goal", value="Backend dev",
            source="goals", confidence=0.9,
        )
        b = upsert_semantic(
            student=student, key="career_goal", value="ML engineer",
            source="dialog", confidence=0.85,
        )
        assert a.id == b.id
        b.refresh_from_db()
        assert b.value == "ML engineer"
        assert b.source == "dialog"


class TestRecordStrategyOutcome:
    def test_increments_counters(self, student):
        record_strategy_outcome(
            student=student, strategy_key="spaced_practice", success=True,
        )
        record_strategy_outcome(
            student=student, strategy_key="spaced_practice", success=False,
        )
        proc = ProceduralMemory.objects.get(
            student=student, strategy_key="spaced_practice",
        )
        assert proc.successes == 1
        assert proc.failures == 1
        # Laplace smoothing: (1+1)/(2+2) = 0.5.
        assert proc.effectiveness_estimate == pytest.approx(0.5)


class TestRecall:
    def test_returns_snapshot(self, student):
        upsert_semantic(student=student, key="career_goal", value="Backend")
        write_episodic(
            student=student, kind="breakthrough",
            summary="Hiểu Hooke", salience=0.9,
        )
        snap = recall(student=student)
        assert isinstance(snap, MemorySnapshot)
        assert any(s["key"] == "career_goal" for s in snap.semantic)
        assert any(e["kind"] == "breakthrough" for e in snap.episodic)

    def test_to_prompt_context_renders_neatly(self, student):
        upsert_semantic(student=student, key="career_goal", value="Backend")
        write_episodic(
            student=student, kind="struggle",
            summary="Vướng tích phân", salience=0.8,
        )
        snap = recall(student=student)
        text = snap.to_prompt_context()
        assert "career_goal" in text
        assert "struggle" in text


class TestViews:
    def test_get_blocked_without_consent(self, student_api):
        resp = student_api.get("/api/coach/memory/me/")
        assert resp.status_code == 403

    def test_get_with_consent(self, student_api, student):
        _grant(student, "agentic_memory")
        upsert_semantic(student=student, key="career_goal", value="Backend")
        resp = student_api.get("/api/coach/memory/me/")
        assert resp.status_code == 200
        assert "semantic" in resp.data
        assert any(s["key"] == "career_goal" for s in resp.data["semantic"])

    def test_delete_works_without_consent(self, student_api, student):
        # Right-to-be-forgotten lever — must always be reachable.
        upsert_semantic(student=student, key="career_goal", value="Backend")
        resp = student_api.delete("/api/coach/memory/me/")
        assert resp.status_code == 200
        assert resp.data["status"] == "memory_cleared"
        assert SemanticMemory.objects.filter(student=student).count() == 0
