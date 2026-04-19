"""Emergency service layer.

The orchestrator calls :func:`escalate` whenever the detector returns
``triggered=True``. The function:

1. Creates an ``EmergencyEvent`` with the SLA target attached.
2. Enqueues every certified counselor (lecturer flag) for the target's
   class. If no counselor exists, fall back to admins so the alert
   never disappears.
3. Schedules the 24/48/72h follow-up timestamps.
4. Sends notifications to all counselors via the in-app dispatcher.

We deliberately avoid touching the chat response — the orchestrator
also gets the detection result and substitutes the safe template.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from emergency.detector import DetectionResult
from emergency.models import (
    CounselorQueueEntry,
    EmergencyContact,
    EmergencyEvent,
)
from notifications.services import dispatch as notify_dispatch

logger = logging.getLogger("palp.emergency")


SAFE_RESPONSE_TEMPLATE = (
    "Mình hiểu bạn đang trải qua điều rất khó khăn. Mình muốn bạn biết bạn "
    "không một mình.\n\n"
    "Ngay bây giờ:\n"
    "- Một counselor sẽ liên hệ bạn trong vòng {sla} phút (đã được thông báo).\n"
    "- Nếu bạn cần ngay: gọi đường dây tư vấn 1800-0011 (miễn phí, 24/7).\n"
    "- Nếu là khẩn cấp đe doạ tính mạng: gọi 115 hoặc đến cơ sở y tế gần nhất.\n\n"
    "Mình sẽ ở đây nếu bạn muốn tiếp tục trò chuyện. Bạn có muốn mình gọi "
    "{contact_name} không?"
)


def safe_response(student) -> str:
    sla = int(getattr(settings, "PALP_EMERGENCY", {}).get("SLA_MINUTES", 15))
    contact = (
        EmergencyContact.objects
        .filter(student=student, consent_given=True)
        .first()
    )
    contact_name = contact.name if contact else "người liên hệ khẩn cấp"
    return SAFE_RESPONSE_TEMPLATE.format(sla=sla, contact_name=contact_name)


@transaction.atomic
def escalate(*, student, detection: DetectionResult, triggering_turn=None) -> EmergencyEvent:
    """Persist + notify. Idempotent within the same turn (one event per turn)."""
    sla_minutes = int(getattr(settings, "PALP_EMERGENCY", {}).get("SLA_MINUTES", 15))
    follow_ups = list(
        getattr(settings, "PALP_EMERGENCY", {}).get("FOLLOW_UP_HOURS", [24, 48, 72])
    )

    if triggering_turn:
        existing = (
            EmergencyEvent.objects
            .filter(triggering_turn=triggering_turn)
            .first()
        )
        if existing:
            return existing

    now = timezone.now()
    event = EmergencyEvent.objects.create(
        student=student,
        triggering_turn=triggering_turn,
        severity=detection.severity or EmergencyEvent.Severity.MEDIUM,
        detected_keywords=detection.matched_keywords,
        detector_score=detection.score,
        detector_notes=detection.notes,
        sla_target_at=now + timedelta(minutes=sla_minutes),
        follow_up_24h_at=now + timedelta(hours=follow_ups[0]) if len(follow_ups) >= 1 else None,
        follow_up_48h_at=now + timedelta(hours=follow_ups[1]) if len(follow_ups) >= 2 else None,
        follow_up_72h_at=now + timedelta(hours=follow_ups[2]) if len(follow_ups) >= 3 else None,
    )

    counselors = list(_counselors_for(student))
    if not counselors:
        counselors = list(_admin_fallback())

    for counselor in counselors:
        CounselorQueueEntry.objects.get_or_create(
            event=event, counselor=counselor,
        )
        notify_dispatch(
            user=counselor,
            category="emergency",
            title=f"Khẩn cấp: {student.username}",
            body=(
                f"Mức độ {event.get_severity_display()}. "
                f"SLA phản hồi: {sla_minutes} phút."
            ),
            severity="urgent",
            deep_link=f"/emergency/{event.id}/",
            payload={"event_id": event.id, "severity": event.severity},
            bypass_preference=True,
        )

    logger.warning(
        "Emergency escalated",
        extra={
            "event_id": event.id,
            "student_id": student.id,
            "severity": event.severity,
            "counselors_notified": len(counselors),
        },
    )
    return event


def acknowledge(*, event: EmergencyEvent, counselor, notes: str = "") -> EmergencyEvent:
    """Counselor accepts the case. Closes the queue entry + records ACK."""
    now = timezone.now()
    if event.status == EmergencyEvent.Status.OPEN:
        event.status = EmergencyEvent.Status.ACKNOWLEDGED
    event.acknowledged_at = now
    event.acknowledged_by = counselor
    if notes:
        event.resolution_notes = (
            f"{event.resolution_notes}\n[ack@{now.isoformat()}]: {notes}"
            if event.resolution_notes else notes
        )
    event.save()

    (
        CounselorQueueEntry.objects
        .filter(event=event, counselor=counselor)
        .update(state=CounselorQueueEntry.State.ACCEPTED, decided_at=now)
    )
    (
        CounselorQueueEntry.objects
        .filter(event=event)
        .exclude(counselor=counselor)
        .filter(state=CounselorQueueEntry.State.QUEUED)
        .update(state=CounselorQueueEntry.State.EXPIRED, decided_at=now)
    )
    return event


def resolve(*, event: EmergencyEvent, counselor, notes: str = "") -> EmergencyEvent:
    """Mark the event resolved. Counselor closure note is appended."""
    now = timezone.now()
    event.status = EmergencyEvent.Status.RESOLVED
    event.resolved_at = now
    if not event.acknowledged_at:
        event.acknowledged_at = now
        event.acknowledged_by = counselor
    if notes:
        event.resolution_notes = (
            f"{event.resolution_notes}\n[resolve@{now.isoformat()}]: {notes}"
            if event.resolution_notes else notes
        )
    event.save()
    return event


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _counselors_for(student):
    """Lecturers assigned to any of the student's classes."""
    from accounts.models import (
        ClassMembership,
        LecturerClassAssignment,
        User,
    )

    class_ids = ClassMembership.objects.filter(
        student=student
    ).values_list("student_class_id", flat=True)
    lecturer_ids = (
        LecturerClassAssignment.objects
        .filter(student_class_id__in=class_ids)
        .values_list("lecturer_id", flat=True)
        .distinct()
    )
    return User.objects.filter(id__in=list(lecturer_ids), is_active=True).order_by("id")


def _admin_fallback():
    from accounts.models import User
    return User.objects.filter(role=User.Role.ADMIN, is_active=True).order_by("id")
