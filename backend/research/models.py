"""IRB-grade research participation models — Phase 7 of v3 MAXIMAL.

Three concerns separated:

* **ResearchProtocol** — admin-defined study description.
* **ResearchParticipation** — opt-in record per (student, protocol).
  Withdrawal is one-click; downstream exports MUST exclude
  withdrawn participants.
* **AnonymizedExport** — append-only log of every dataset export
  taken under a protocol, with the k-anonymity check result.

Anonymisation logic itself lives in ``research/services.py``.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models


class ResearchProtocol(models.Model):
    """One IRB-style study description."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Bản nháp"
        APPROVED = "approved", "Đã phê duyệt"
        ACTIVE = "active", "Đang chạy"
        CLOSED = "closed", "Đã đóng"

    code = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=240)
    description = models.TextField()
    pi_name = models.CharField(max_length=160, blank=True)
    pi_email = models.EmailField(blank=True)
    irb_number = models.CharField(max_length=80, blank=True)
    data_purposes = models.JSONField(
        default=list, blank=True,
        help_text="List of declared purposes (e.g. 'aied_2026_dkt_replication').",
    )
    data_categories = models.JSONField(
        default=list, blank=True,
        help_text="Categories of data this protocol consumes (academic, behavioral, …).",
    )
    retention_months = models.PositiveSmallIntegerField(default=12)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_research_protocol"

    def __str__(self) -> str:
        return f"{self.code} [{self.status}]"


class ResearchParticipation(models.Model):
    """Per (student, protocol) opt-in record."""

    class State(models.TextChoices):
        OPTED_IN = "opted_in", "Đã tham gia"
        WITHDRAWN = "withdrawn", "Đã rút"
        DECLINED = "declined", "Đã từ chối"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="research_participations",
    )
    protocol = models.ForeignKey(
        ResearchProtocol,
        on_delete=models.CASCADE,
        related_name="participations",
    )
    state = models.CharField(max_length=16, choices=State.choices)
    consent_text_version = models.CharField(
        max_length=20,
        help_text="Snapshot of which consent-text version the student agreed to.",
    )
    decided_at = models.DateTimeField(auto_now_add=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "palp_research_participation"
        indexes = [
            models.Index(fields=["protocol", "state"]),
            models.Index(fields=["student", "-decided_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "protocol"],
                name="uq_research_participation_student_protocol",
            ),
        ]

    def __str__(self) -> str:
        return f"Part({self.student_id} ↔ {self.protocol.code}, {self.state})"


class AnonymizedExport(models.Model):
    """Append-only log — what data left under what protocol, with k-anon check."""

    protocol = models.ForeignKey(
        ResearchProtocol,
        on_delete=models.PROTECT,
        related_name="exports",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="anonymized_exports",
    )
    dataset_key = models.CharField(
        max_length=80,
        help_text="What dataset was exported (e.g. 'attempts_q1_2026').",
    )
    record_count = models.PositiveIntegerField(default=0)
    participant_count = models.PositiveIntegerField(default=0)
    k_anonymity_value = models.PositiveSmallIntegerField(default=0)
    k_anonymity_passed = models.BooleanField(default=False)
    suppressed_columns = models.JSONField(default=list, blank=True)
    salt_id = models.CharField(
        max_length=80, blank=True,
        help_text="Hash salt key reference; never store the salt itself here.",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_research_anonymized_export"
        indexes = [
            models.Index(fields=["protocol", "-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return (
            f"Export({self.dataset_key}, n={self.record_count}, "
            f"k={self.k_anonymity_value}, ok={self.k_anonymity_passed})"
        )
