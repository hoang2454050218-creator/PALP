"""Emergency Pipeline models — Phase 4 of v3 MAXIMAL roadmap.

Per ``docs/COACH_SAFETY_PLAYBOOK.md`` section 9 + the dedicated
``EMERGENCY_RESPONSE_TRAINING.md`` playbook, the system needs:

* a way to record an emergency event for audit / postmortem
  (``EmergencyEvent``),
* an opt-in emergency contact for the student (``EmergencyContact``),
* a queue entry per certified counselor consumer
  (``CounselorQueueEntry``).

The 15-minute SLA in the design doc is enforced at the service layer,
not via a DB constraint, so we can re-use the same models for
post-incident review (the SLA target stays a column for analytics).
"""
from __future__ import annotations

from django.conf import settings
from django.db import models


class EmergencyEvent(models.Model):
    """One mental-health / safety event detected from a coach turn."""

    class Severity(models.TextChoices):
        MEDIUM = "medium", "Trung bình"
        HIGH = "high", "Cao"
        CRITICAL = "critical", "Nguy cấp"

    class Status(models.TextChoices):
        OPEN = "open", "Đang mở"
        ACKNOWLEDGED = "acknowledged", "Counselor đã xác nhận"
        RESOLVED = "resolved", "Đã giải quyết"
        ESCALATED = "escalated", "Đã leo thang tiếp"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="emergency_events",
    )
    triggering_turn = models.ForeignKey(
        "coach.CoachTurn",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="emergency_events",
    )

    severity = models.CharField(max_length=16, choices=Severity.choices)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.OPEN,
    )

    detected_keywords = models.JSONField(default=list, blank=True)
    detector_score = models.FloatField(default=0.0)
    detector_notes = models.TextField(blank=True)

    detected_at = models.DateTimeField(auto_now_add=True)
    sla_target_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When this event must be acknowledged by a counselor (15-min SLA).",
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="acknowledged_emergencies",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    follow_up_24h_at = models.DateTimeField(null=True, blank=True)
    follow_up_48h_at = models.DateTimeField(null=True, blank=True)
    follow_up_72h_at = models.DateTimeField(null=True, blank=True)

    contacted_emergency_contact = models.BooleanField(default=False)

    class Meta:
        db_table = "palp_emergency_event"
        indexes = [
            models.Index(fields=["status", "-detected_at"]),
            models.Index(fields=["severity", "-detected_at"]),
            models.Index(fields=["student", "-detected_at"]),
        ]

    def __str__(self) -> str:
        return f"Emergency({self.id}) {self.student.username} sev={self.severity}"


class EmergencyContact(models.Model):
    """Opt-in emergency contact a student adds for safety escalation."""

    class Relationship(models.TextChoices):
        PARENT = "parent", "Phụ huynh"
        SIBLING = "sibling", "Anh chị em"
        FRIEND = "friend", "Bạn"
        COUNSELOR = "counselor", "Cố vấn"
        OTHER = "other", "Khác"

    student = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="emergency_contact",
    )
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    relationship = models.CharField(
        max_length=16, choices=Relationship.choices, default=Relationship.OTHER,
    )

    consent_given = models.BooleanField(default=False)
    consent_given_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_emergency_contact"

    def __str__(self) -> str:
        return f"EC({self.student.username}) -> {self.name} [{self.relationship}]"


class CounselorQueueEntry(models.Model):
    """One row per (event, counselor) target — many counselors can be notified per event."""

    class State(models.TextChoices):
        QUEUED = "queued", "Trong hàng đợi"
        VIEWED = "viewed", "Đã xem"
        ACCEPTED = "accepted", "Đã nhận"
        DECLINED = "declined", "Đã từ chối"
        EXPIRED = "expired", "Đã hết hạn"

    event = models.ForeignKey(
        EmergencyEvent,
        on_delete=models.CASCADE,
        related_name="queue_entries",
    )
    counselor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="counselor_queue_entries",
    )
    state = models.CharField(
        max_length=16, choices=State.choices, default=State.QUEUED,
    )
    queued_at = models.DateTimeField(auto_now_add=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "palp_counselor_queue"
        indexes = [
            models.Index(fields=["counselor", "state", "-queued_at"]),
            models.Index(fields=["event", "state"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["event", "counselor"],
                name="uq_counselor_queue_event_counselor",
            ),
        ]

    def __str__(self) -> str:
        return f"CQ(event={self.event_id}, counselor={self.counselor_id}, {self.state})"
