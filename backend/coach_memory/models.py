"""Agentic Coach Memory — Phase 5 of v3 MAXIMAL roadmap.

Implements the 3-layer Letta/MemGPT-inspired memory architecture
called for in ``docs/AI_COACH_ARCHITECTURE.md`` section 4 (P5):

* **EpisodicMemory** — timeline of "what happened":
  struggles, breakthroughs, sessions. Append-only.
* **SemanticMemory** — long-lived facts about the student
  (career goal, learning preferences). Upserted.
* **ProceduralMemory** — what worked / didn't work for THIS student
  (e.g. "spaced practice nudge → +30% completion"). Updated by the
  bandit / causal evaluator.

The recall path (used by the coach to inject memory into the system
prompt) lives in ``services.recall``. None of the LLM-side prompt
construction lives here — keeping memory decoupled from the coach lets
the same memory feed the bandit and the lecturer view too.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models


class EpisodicMemory(models.Model):
    """One thing that happened to the student.

    Append-only. Older episodes are summarised by the periodic
    ``coach_memory.tasks.compact_old_episodes`` job into shorter
    aggregate episodes so the recall window stays bounded.
    """

    class Kind(models.TextChoices):
        STRUGGLE = "struggle", "Vật lộn với concept"
        BREAKTHROUGH = "breakthrough", "Đột phá / hiểu ra"
        REFLECTION = "reflection", "Phản tỉnh tuần"
        EMERGENCY = "emergency", "Sự kiện khẩn cấp"
        PEER_SESSION = "peer_session", "Phiên dạy nhau"
        COACH_TURN = "coach_turn", "Một lượt với coach"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="episodic_memories",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    summary = models.CharField(
        max_length=240,
        help_text="One-sentence summary; never the raw message body.",
    )
    detail = models.JSONField(
        default=dict, blank=True,
        help_text="Structured payload (concept_id, score, etc). NEVER a verbatim message.",
    )
    salience = models.FloatField(
        default=0.5,
        help_text="0..1 — how relevant this episode is for recall.",
    )
    occurred_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_memory_episodic"
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["student", "-occurred_at"]),
            models.Index(fields=["student", "kind", "-occurred_at"]),
        ]

    def __str__(self) -> str:
        return f"Episodic({self.student_id}, {self.kind}, {self.occurred_at:%Y-%m-%d})"


class SemanticMemory(models.Model):
    """Long-lived facts about the student.

    One row per (student, key). ``key`` is a slug like
    ``career_goal``, ``preferred_explanation_style``, ``time_of_day``.
    Upserted; never deleted unless the student revokes
    ``agentic_memory`` consent.
    """

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="semantic_memories",
    )
    key = models.SlugField(max_length=80)
    value = models.JSONField(default=dict, blank=True)
    confidence = models.FloatField(default=0.7)
    source = models.CharField(
        max_length=40, blank=True,
        help_text="Where the fact came from (goals.career_goal, coach.dialog, …).",
    )
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_memory_semantic"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "key"],
                name="uq_semantic_student_key",
            ),
        ]
        indexes = [
            models.Index(fields=["student", "key"]),
        ]

    def __str__(self) -> str:
        return f"Semantic({self.student_id}, {self.key})"


class ProceduralMemory(models.Model):
    """What strategy / nudge / arm worked for THIS student.

    Updated by the bandit's reward stream. Higher
    ``effectiveness_estimate`` => coach prefers this strategy when
    suggesting next steps to the student.
    """

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="procedural_memories",
    )
    strategy_key = models.SlugField(
        max_length=80,
        help_text="e.g. 'spaced_practice_nudge', 'morning_session', 'peer_session'.",
    )
    successes = models.PositiveIntegerField(default=0)
    failures = models.PositiveIntegerField(default=0)
    effectiveness_estimate = models.FloatField(
        default=0.5,
        help_text="0..1 — running estimate of P(success | strategy applied).",
    )
    last_applied_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_memory_procedural"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "strategy_key"],
                name="uq_procedural_student_strategy",
            ),
        ]
        indexes = [
            models.Index(fields=["student", "-effectiveness_estimate"]),
        ]

    def __str__(self) -> str:
        return (
            f"Procedural({self.student_id}, {self.strategy_key}, "
            f"eff={self.effectiveness_estimate:.2f})"
        )
