"""Agentic memory service layer.

The four public functions (``write_episodic``, ``upsert_semantic``,
``record_strategy_outcome``, ``recall``) deliberately avoid coupling
to the coach orchestrator — anything that wants to teach the memory
about an event (peer engine after a session, goals app after a
reflection, bandit after a reward) calls these helpers directly.

``recall`` is what the coach orchestrator injects into the system
prompt. It returns a small, bounded summary so the system prompt
stays under the LLM's context budget.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from django.db import transaction
from django.utils import timezone

from coach_memory.models import (
    EpisodicMemory,
    ProceduralMemory,
    SemanticMemory,
)


@dataclass
class MemorySnapshot:
    semantic: list[dict] = field(default_factory=list)
    episodic: list[dict] = field(default_factory=list)
    procedural: list[dict] = field(default_factory=list)

    def to_prompt_context(self) -> str:
        """Render the snapshot as a short, neutral context string."""
        chunks: list[str] = []
        if self.semantic:
            chunks.append("Semantic facts:")
            for s in self.semantic[:5]:
                chunks.append(f"- {s['key']}: {_short(s['value'])}")
        if self.procedural:
            chunks.append("What worked recently:")
            for p in self.procedural[:5]:
                chunks.append(
                    f"- {p['strategy_key']} (eff≈{p['effectiveness_estimate']:.2f})"
                )
        if self.episodic:
            chunks.append("Recent timeline:")
            for e in self.episodic[:5]:
                chunks.append(f"- [{e['kind']}] {e['summary']}")
        if not chunks:
            return ""
        return "\n".join(chunks)


# ---------------------------------------------------------------------------
# Public API — write side
# ---------------------------------------------------------------------------

def write_episodic(
    *,
    student,
    kind: str,
    summary: str,
    detail: dict | None = None,
    salience: float = 0.5,
    occurred_at=None,
) -> EpisodicMemory:
    return EpisodicMemory.objects.create(
        student=student,
        kind=kind,
        summary=summary[:240],
        detail=detail or {},
        salience=max(0.0, min(1.0, float(salience))),
        occurred_at=occurred_at or timezone.now(),
    )


@transaction.atomic
def upsert_semantic(
    *,
    student,
    key: str,
    value,
    confidence: float = 0.7,
    source: str = "",
) -> SemanticMemory:
    obj, _ = SemanticMemory.objects.update_or_create(
        student=student,
        key=key,
        defaults={
            "value": _coerce_value(value),
            "confidence": max(0.0, min(1.0, float(confidence))),
            "source": source,
        },
    )
    return obj


@transaction.atomic
def record_strategy_outcome(
    *,
    student,
    strategy_key: str,
    success: bool,
    notes: str = "",
) -> ProceduralMemory:
    obj, _ = ProceduralMemory.objects.select_for_update().get_or_create(
        student=student, strategy_key=strategy_key,
    )
    if success:
        obj.successes += 1
    else:
        obj.failures += 1
    total = obj.successes + obj.failures
    # Laplace smoothing so a single success doesn't claim 100%.
    obj.effectiveness_estimate = (obj.successes + 1.0) / (total + 2.0)
    obj.last_applied_at = timezone.now()
    if notes:
        obj.notes = (obj.notes + "\n" + notes).strip()
    obj.save()
    return obj


# ---------------------------------------------------------------------------
# Public API — read side
# ---------------------------------------------------------------------------

def recall(
    *,
    student,
    intent: str = "",
    max_episodic: int = 5,
    max_semantic: int = 5,
    max_procedural: int = 3,
) -> MemorySnapshot:
    """Return a bounded snapshot of what the coach should remember.

    Future work (Phase 5B): use a vector index for similarity search;
    today we just sort by recency + salience because the dataset is
    tiny.
    """
    semantic_qs = (
        SemanticMemory.objects
        .filter(student=student)
        .order_by("-confidence", "-updated_at")[:max_semantic]
    )
    episodic_qs = (
        EpisodicMemory.objects
        .filter(student=student)
        .order_by("-salience", "-occurred_at")[:max_episodic]
    )
    procedural_qs = (
        ProceduralMemory.objects
        .filter(student=student)
        .order_by("-effectiveness_estimate")[:max_procedural]
    )

    semantic = [
        {
            "key": s.key,
            "value": s.value,
            "confidence": s.confidence,
            "source": s.source,
            "updated_at": s.updated_at.isoformat(),
        }
        for s in semantic_qs
    ]
    episodic = [
        {
            "kind": e.kind,
            "summary": e.summary,
            "detail": e.detail,
            "salience": e.salience,
            "occurred_at": e.occurred_at.isoformat(),
        }
        for e in episodic_qs
    ]
    procedural = [
        {
            "strategy_key": p.strategy_key,
            "successes": p.successes,
            "failures": p.failures,
            "effectiveness_estimate": p.effectiveness_estimate,
            "last_applied_at": (
                p.last_applied_at.isoformat() if p.last_applied_at else None
            ),
        }
        for p in procedural_qs
    ]

    return MemorySnapshot(
        semantic=semantic, episodic=episodic, procedural=procedural,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _coerce_value(value):
    if isinstance(value, (dict, list, str, int, float, bool)):
        return value
    if value is None:
        return None
    return str(value)


def _short(value, max_len: int = 80) -> str:
    if isinstance(value, dict):
        items = ", ".join(f"{k}={v}" for k, v in list(value.items())[:3])
        text = f"{{{items}}}"
    else:
        text = str(value)
    return text if len(text) <= max_len else text[: max_len - 1] + "…"
