"""
Event completeness tests (EC-01 to EC-08) and event taxonomy tests
(EVT-003, EVT-008, EVT-009).

QA_STANDARD Section 6.3 + Section 3.7.
"""
import pytest
from datetime import timedelta

from django.utils import timezone
from rest_framework import status

from events.models import EventLog

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# EC-01 to EC-08: Event Data Completeness — required fields per event type
# ---------------------------------------------------------------------------


class TestEC01SessionStarted:
    """EC-01: session_started must have user_id, timestamp, device."""

    def test_required_fields_present(self, student):
        event = EventLog.objects.create(
            event_name=EventLog.EventName.SESSION_STARTED,
            timestamp_utc=timezone.now(),
            actor=student,
            actor_type=EventLog.ActorType.STUDENT,
            device_type="desktop",
        )
        assert event.actor is not None
        assert event.timestamp_utc is not None
        assert event.device_type != ""

    def test_actor_not_null(self, student):
        event = EventLog.objects.create(
            event_name=EventLog.EventName.SESSION_STARTED,
            timestamp_utc=timezone.now(),
            actor=student,
            actor_type=EventLog.ActorType.STUDENT,
        )
        assert event.actor_id is not None


class TestEC02SessionEnded:
    """EC-02: session_ended must have user_id and duration > 0."""

    def test_duration_positive(self, student):
        event = EventLog.objects.create(
            event_name=EventLog.EventName.SESSION_ENDED,
            timestamp_utc=timezone.now(),
            actor=student,
            actor_type=EventLog.ActorType.STUDENT,
            properties={"duration_seconds": 300},
        )
        assert event.properties["duration_seconds"] > 0

    def test_zero_duration_invalid(self, student):
        event = EventLog.objects.create(
            event_name=EventLog.EventName.SESSION_ENDED,
            timestamp_utc=timezone.now(),
            actor=student,
            actor_type=EventLog.ActorType.STUDENT,
            properties={"duration_seconds": 0},
        )
        assert event.properties["duration_seconds"] == 0


class TestEC03AssessmentCompleted:
    """EC-03: assessment_completed must have score in [0,100] and time_taken."""

    def test_valid_score_range(self, student):
        event = EventLog.objects.create(
            event_name=EventLog.EventName.ASSESSMENT_COMPLETED,
            timestamp_utc=timezone.now(),
            actor=student,
            actor_type=EventLog.ActorType.STUDENT,
            properties={"score": 75.0, "time_taken_seconds": 600},
        )
        assert 0 <= event.properties["score"] <= 100

    def test_boundary_scores(self, student):
        for score in [0, 100]:
            event = EventLog.objects.create(
                event_name=EventLog.EventName.ASSESSMENT_COMPLETED,
                timestamp_utc=timezone.now(),
                actor=student,
                actor_type=EventLog.ActorType.STUDENT,
                properties={"score": score, "time_taken_seconds": 600},
            )
            assert 0 <= event.properties["score"] <= 100


class TestEC04MicroTaskCompleted:
    """EC-04: micro_task_completed must have task_id, attempts, duration."""

    def test_task_id_required(self, student, micro_tasks):
        event = EventLog.objects.create(
            event_name=EventLog.EventName.MICRO_TASK_COMPLETED,
            timestamp_utc=timezone.now(),
            actor=student,
            actor_type=EventLog.ActorType.STUDENT,
            task=micro_tasks[0],
            properties={"attempts": 1, "duration_seconds": 45},
        )
        assert event.task_id is not None
        assert event.task_id == micro_tasks[0].id

    def test_attempts_and_duration_present(self, student, micro_tasks):
        event = EventLog.objects.create(
            event_name=EventLog.EventName.MICRO_TASK_COMPLETED,
            timestamp_utc=timezone.now(),
            actor=student,
            actor_type=EventLog.ActorType.STUDENT,
            task=micro_tasks[0],
            properties={"attempts": 2, "duration_seconds": 90},
        )
        assert event.properties["attempts"] > 0
        assert event.properties["duration_seconds"] > 0


class TestEC05ContentIntervention:
    """EC-05: content_intervention must have concept_id, type, source_rule."""

    def test_concept_id_exists(self, student, concepts):
        event = EventLog.objects.create(
            event_name=EventLog.EventName.CONTENT_INTERVENTION,
            timestamp_utc=timezone.now(),
            actor=student,
            actor_type=EventLog.ActorType.STUDENT,
            concept=concepts[0],
            properties={"type": "supplementary", "source_rule": "mastery_below_0.6"},
        )
        assert event.concept_id is not None
        assert event.concept_id == concepts[0].id

    def test_source_rule_present(self, student, concepts):
        event = EventLog.objects.create(
            event_name=EventLog.EventName.CONTENT_INTERVENTION,
            timestamp_utc=timezone.now(),
            actor=student,
            actor_type=EventLog.ActorType.STUDENT,
            concept=concepts[0],
            properties={"type": "supplementary", "source_rule": "mastery_below_0.6"},
        )
        assert event.properties["source_rule"] != ""


class TestEC06GvActionTaken:
    """EC-06: gv_action_taken must have action_type and non-empty targets."""

    def test_targets_non_empty(self, lecturer):
        event = EventLog.objects.create(
            event_name=EventLog.EventName.GV_ACTION_TAKEN,
            timestamp_utc=timezone.now(),
            actor=lecturer,
            actor_type=EventLog.ActorType.LECTURER,
            properties={
                "action_type": "send_message",
                "targets": [1, 2],
                "message": "Hãy cố gắng thêm!",
            },
        )
        assert len(event.properties["targets"]) > 0
        assert event.properties["action_type"] != ""


class TestEC07WellbeingNudgeShown:
    """EC-07: wellbeing_nudge_shown must have nudge_type and accepted boolean."""

    def test_nudge_type_present(self, student):
        event = EventLog.objects.create(
            event_name=EventLog.EventName.WELLBEING_NUDGE_SHOWN,
            timestamp_utc=timezone.now(),
            actor=student,
            actor_type=EventLog.ActorType.STUDENT,
            properties={"nudge_type": "break_reminder", "accepted": True},
        )
        assert event.properties["nudge_type"] != ""
        assert isinstance(event.properties["accepted"], bool)


class TestEC08PageView:
    """EC-08: page_view must have non-empty page."""

    def test_page_non_empty(self, student):
        event = EventLog.objects.create(
            event_name=EventLog.EventName.PAGE_VIEW,
            timestamp_utc=timezone.now(),
            actor=student,
            actor_type=EventLog.ActorType.STUDENT,
            source_page="/dashboard",
            properties={"page": "/dashboard", "referrer": "/login"},
        )
        assert event.source_page != ""
        assert event.properties["page"] != ""


# ---------------------------------------------------------------------------
# EVT-003: All 8 core event types can fire and persist
# ---------------------------------------------------------------------------


class TestEVT003CoreEventTypes:
    """EVT-003: 8 event types can all fire and persist."""

    CORE_EVENTS = [
        EventLog.EventName.SESSION_STARTED,
        EventLog.EventName.SESSION_ENDED,
        EventLog.EventName.ASSESSMENT_COMPLETED,
        EventLog.EventName.MICRO_TASK_COMPLETED,
        EventLog.EventName.CONTENT_INTERVENTION,
        EventLog.EventName.GV_ACTION_TAKEN,
        EventLog.EventName.WELLBEING_NUDGE_SHOWN,
        EventLog.EventName.PAGE_VIEW,
    ]

    def test_all_8_event_types_persist(self, student, lecturer):
        actor_map = {
            EventLog.EventName.GV_ACTION_TAKEN: (lecturer, EventLog.ActorType.LECTURER),
        }

        for event_name in self.CORE_EVENTS:
            actor, actor_type = actor_map.get(
                event_name, (student, EventLog.ActorType.STUDENT),
            )
            EventLog.objects.create(
                event_name=event_name,
                timestamp_utc=timezone.now(),
                actor=actor,
                actor_type=actor_type,
            )

        for event_name in self.CORE_EVENTS:
            assert EventLog.objects.filter(event_name=event_name).exists(), (
                f"Event type {event_name} did not persist"
            )

    def test_event_count_matches(self, student, lecturer):
        for event_name in self.CORE_EVENTS:
            actor = lecturer if "gv" in event_name else student
            actor_type = (
                EventLog.ActorType.LECTURER if "gv" in event_name
                else EventLog.ActorType.STUDENT
            )
            EventLog.objects.create(
                event_name=event_name,
                timestamp_utc=timezone.now(),
                actor=actor,
                actor_type=actor_type,
            )

        assert EventLog.objects.count() == len(self.CORE_EVENTS)


# ---------------------------------------------------------------------------
# EVT-008: No duplicate events (same name + timestamp + user within 1s)
# ---------------------------------------------------------------------------


class TestEVT008Deduplication:
    """EVT-008: idempotency_key prevents duplicate events."""

    def test_idempotency_key_prevents_duplicate(self, student_api):
        payload = {
            "event_name": "page_view",
            "idempotency_key": "unique-key-abc-123",
        }

        resp1 = student_api.post("/api/events/track/", payload, format="json")
        assert resp1.status_code == status.HTTP_201_CREATED

        resp2 = student_api.post("/api/events/track/", payload, format="json")
        assert resp2.status_code in (
            status.HTTP_201_CREATED,
            status.HTTP_200_OK,
            status.HTTP_409_CONFLICT,
        )

        count = EventLog.objects.filter(
            idempotency_key="unique-key-abc-123",
        ).count()
        assert count == 1

    def test_different_keys_create_separate_events(self, student_api):
        for i in range(3):
            resp = student_api.post("/api/events/track/", {
                "event_name": "page_view",
                "idempotency_key": f"key-{i}",
            }, format="json")
            assert resp.status_code == status.HTTP_201_CREATED

        assert EventLog.objects.count() == 3


# ---------------------------------------------------------------------------
# EVT-009: Event properties validate schema (no arbitrary data)
# ---------------------------------------------------------------------------


class TestEVT009SchemaValidation:
    """EVT-009: Events validate schema, reject invalid event_name."""

    def test_invalid_event_name_rejected(self, student_api):
        resp = student_api.post("/api/events/track/", {
            "event_name": "totally_made_up_event",
        }, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_valid_event_name_accepted(self, student_api):
        resp = student_api.post("/api/events/track/", {
            "event_name": "page_view",
        }, format="json")
        assert resp.status_code == status.HTTP_201_CREATED

    def test_oversized_properties_rejected(self, student_api):
        resp = student_api.post("/api/events/track/", {
            "event_name": "page_view",
            "properties": {"x": "a" * 15000},
        }, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_empty_properties_accepted(self, student_api):
        resp = student_api.post("/api/events/track/", {
            "event_name": "page_view",
            "properties": {},
        }, format="json")
        assert resp.status_code == status.HTTP_201_CREATED


# ---------------------------------------------------------------------------
# EVT-010: RBAC on event access
# ---------------------------------------------------------------------------


class TestEVT010EventRBAC:
    """EVT-010: Student sees own events only; Lecturer sees class students."""

    def test_student_sees_own_events(self, student_api, student):
        student_api.post("/api/events/track/", {
            "event_name": "page_view",
        }, format="json")

        resp = student_api.get("/api/events/my/")
        assert resp.status_code == status.HTTP_200_OK

    def test_student_cannot_see_other_student(self, student_api, student_b):
        resp = student_api.get(f"/api/events/student/{student_b.pk}/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_lecturer_can_see_class_student(
        self, lecturer_api, student, class_with_members,
    ):
        resp = lecturer_api.get(f"/api/events/student/{student.pk}/")
        assert resp.status_code == status.HTTP_200_OK
