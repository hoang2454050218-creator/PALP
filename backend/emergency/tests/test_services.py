"""Emergency escalation service tests."""
from __future__ import annotations

import pytest

from emergency.detector import DetectionResult
from emergency.models import (
    CounselorQueueEntry,
    EmergencyEvent,
)
from emergency.services import acknowledge, escalate, resolve, safe_response
from notifications.models import Notification


pytestmark = pytest.mark.django_db


def _detection(severity="critical"):
    return DetectionResult(
        triggered=True,
        severity=severity,
        matched_keywords=["tự tử"],
        score=0.95,
        notes="test",
    )


class TestEscalate:
    def test_creates_event_with_sla(self, class_with_members, student, lecturer):
        event = escalate(student=student, detection=_detection())
        assert isinstance(event, EmergencyEvent)
        assert event.severity == "critical"
        assert event.sla_target_at is not None

    def test_enqueues_assigned_counselor(self, class_with_members, student, lecturer):
        event = escalate(student=student, detection=_detection())
        entries = list(CounselorQueueEntry.objects.filter(event=event))
        assert len(entries) == 1
        assert entries[0].counselor_id == lecturer.id

    def test_dispatches_notification(self, class_with_members, student, lecturer):
        escalate(student=student, detection=_detection())
        notif = Notification.objects.filter(
            user=lecturer, category="emergency",
        ).first()
        assert notif is not None
        assert notif.severity == "urgent"

    def test_falls_back_to_admin_when_no_counselor(self, student, admin_user):
        # student has NO class membership / lecturer assignment.
        event = escalate(student=student, detection=_detection())
        entry = CounselorQueueEntry.objects.filter(event=event).first()
        assert entry is not None
        assert entry.counselor_id == admin_user.id

    def test_idempotent_for_same_turn(self, student, admin_user):
        from coach.models import CoachConversation, CoachTurn

        conv = CoachConversation.objects.create(student=student)
        turn = CoachTurn.objects.create(
            conversation=conv, turn_number=1,
            role=CoachTurn.Role.STUDENT, content="x",
        )
        a = escalate(student=student, detection=_detection(), triggering_turn=turn)
        b = escalate(student=student, detection=_detection(), triggering_turn=turn)
        assert a.id == b.id


class TestAcknowledge:
    def test_marks_event_and_queue(self, class_with_members, student, lecturer):
        event = escalate(student=student, detection=_detection())
        event = acknowledge(event=event, counselor=lecturer, notes="took it")
        assert event.status == EmergencyEvent.Status.ACKNOWLEDGED
        assert event.acknowledged_by_id == lecturer.id
        entry = CounselorQueueEntry.objects.get(event=event, counselor=lecturer)
        assert entry.state == CounselorQueueEntry.State.ACCEPTED


class TestResolve:
    def test_marks_event_resolved(self, class_with_members, student, lecturer):
        event = escalate(student=student, detection=_detection())
        event = resolve(event=event, counselor=lecturer, notes="ok")
        assert event.status == EmergencyEvent.Status.RESOLVED
        assert event.resolved_at is not None


class TestSafeResponse:
    def test_safe_response_includes_hotline(self, student):
        text = safe_response(student)
        assert "1800-0011" in text
        assert "115" in text
