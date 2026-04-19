"""Coach models — Phase 4 of v3 MAXIMAL roadmap.

Implements the data layer for the Hybrid AI Coach described in
``docs/AI_COACH_ARCHITECTURE.md`` + ``docs/COACH_SAFETY_PLAYBOOK.md``.

Key separation of concerns:

* **CoachConsent** — per-feature opt-in flags. ``ai_coach_local`` is the
  default-safe option; ``ai_coach_cloud`` requires explicit opt-in
  because cloud LLM calls leave the infra. ``share_emergency_contact``
  is the privacy-sensitive flag the Emergency pipeline reads.
* **CoachConversation** — one chat thread per user. Open conversations
  are reused; explicit ``end()`` archives them.
* **CoachTurn** — one user-message ↔ assistant-response pair, including
  the LLM provider that handled it. Encrypted ``content`` keeps the
  body separate from the audit log so the latter can stay PII-light
  per the playbook's "never log message text" rule.
* **CoachAuditLog** — ONE row per turn capturing only the safety/cost
  metadata (provider, tokens, refusal flags, hallucination findings,
  PII token counts). Designed so a security review can see what
  happened without ever needing message bodies.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models


class CoachConsent(models.Model):
    """Per-student opt-in flags for the coach features."""

    student = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="coach_consent",
    )
    ai_coach_local = models.BooleanField(
        default=True,
        help_text="Local LLM dialog. PII never leaves infrastructure.",
    )
    ai_coach_cloud = models.BooleanField(
        default=False,
        help_text="Cloud LLM dialog (Anthropic/OpenAI). Requires explicit opt-in.",
    )
    share_emergency_contact = models.BooleanField(
        default=False,
        help_text="Allow Emergency Pipeline to contact your emergency contact.",
    )

    cooldown_until = models.DateTimeField(
        null=True, blank=True,
        help_text="If set, coach refuses messages until this time (e.g. after 3 jailbreak attempts).",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_coach_consent"

    def __str__(self) -> str:
        return f"CoachConsent({self.student.username})"


class CoachConversation(models.Model):
    """A coach chat thread.

    One open thread per (student, started_at). When the student or
    system ends the thread, ``ended_at`` is set and a new thread starts
    on the next message. Keeps thread context bounded for memory and
    privacy.
    """

    class Status(models.TextChoices):
        OPEN = "open", "Đang mở"
        ENDED = "ended", "Đã kết thúc"
        SYSTEM_CLOSED = "system_closed", "Hệ thống đóng (cooldown / safety)"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="coach_conversations",
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.OPEN,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    last_intent = models.CharField(max_length=40, blank=True)
    turn_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "palp_coach_conversation"
        indexes = [
            models.Index(fields=["student", "status"]),
            models.Index(fields=["student", "-started_at"]),
        ]

    def __str__(self) -> str:
        return f"Conv({self.id}) {self.student.username} [{self.status}] turns={self.turn_count}"


class CoachTurn(models.Model):
    """One round-trip in a CoachConversation.

    The full request/response bodies live here so the audit table next
    door can stay PII-light. Both fields are stored as text — disk-level
    encryption is the responsibility of the database (PALP runs Postgres
    with TDE in production); we don't double-encrypt application-side
    because per-row decryption breaks pgvector + ANALYZE.
    """

    class Role(models.TextChoices):
        STUDENT = "student", "Sinh viên"
        ASSISTANT = "assistant", "Coach"
        SYSTEM = "system", "Hệ thống"

    conversation = models.ForeignKey(
        CoachConversation,
        on_delete=models.CASCADE,
        related_name="turns",
    )
    turn_number = models.PositiveIntegerField()
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()

    intent = models.CharField(max_length=40, blank=True)
    llm_provider = models.CharField(max_length=20, blank=True)
    llm_model = models.CharField(max_length=60, blank=True)

    safety_flags = models.JSONField(
        default=list, blank=True,
        help_text="List of safety findings for this turn (refusal, jailbreak, etc).",
    )
    refusal_triggered = models.BooleanField(default=False)
    emergency_triggered = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_coach_turn"
        ordering = ["conversation", "turn_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "turn_number"],
                name="uq_coach_turn_seq",
            ),
        ]

    def __str__(self) -> str:
        return f"Turn({self.conversation_id}#{self.turn_number}) {self.role}"


class CoachAuditLog(models.Model):
    """PII-light audit log for the safety / cost layer.

    One row per ``CoachTurn`` (assistant turn). NEVER stores the message
    body — only the metadata required by the
    ``COACH_SAFETY_PLAYBOOK`` table in section 11. This is the table a
    security review can pull without needing to decrypt messages.
    """

    turn = models.OneToOneField(
        CoachTurn, on_delete=models.CASCADE, related_name="audit",
    )
    request_id = models.CharField(max_length=64, blank=True)

    intent = models.CharField(max_length=40, blank=True)
    llm_provider = models.CharField(max_length=20, blank=True)
    llm_model = models.CharField(max_length=60, blank=True)

    tokens_in = models.PositiveIntegerField(default=0)
    tokens_out = models.PositiveIntegerField(default=0)
    latency_ms = models.PositiveIntegerField(default=0)

    tools_called = models.JSONField(default=list, blank=True)
    safety_flags = models.JSONField(default=list, blank=True)
    pii_tokens_count = models.PositiveIntegerField(default=0)
    canary_check_passed = models.BooleanField(default=True)
    hallucination_findings = models.JSONField(default=list, blank=True)
    refusal_triggered = models.BooleanField(default=False)
    emergency_triggered = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_coach_audit"
        indexes = [
            models.Index(fields=["llm_provider", "-created_at"]),
            models.Index(fields=["refusal_triggered", "-created_at"]),
            models.Index(fields=["emergency_triggered", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"Audit(turn={self.turn_id}) provider={self.llm_provider}"
