"""
Observability and Instrumentation Tests.

QA_STANDARD Section 7.3.
Verifies event quality, completeness, deduplication, clock handling,
and confirmation for critical events.
"""
import pytest
from datetime import timedelta

from django.utils import timezone

from events.models import EventLog

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


REQUIRED_BASE_FIELDS = [
    "event_name", "event_version", "timestamp_utc",
    "actor_type", "request_id",
]

LEARNING_EVENTS = {
    EventLog.EventName.MICRO_TASK_COMPLETED,
    EventLog.EventName.CONTENT_INTERVENTION,
    EventLog.EventName.RETRY_TRIGGERED,
}

CONFIRMATION_EVENTS = {
    EventLog.EventName.ASSESSMENT_COMPLETED,
    EventLog.EventName.MICRO_TASK_COMPLETED,
    EventLog.EventName.GV_ACTION_TAKEN,
}


# ---------------------------------------------------------------------------
# OB-01: Event completeness >= 99.5%
# ---------------------------------------------------------------------------


class TestOB01EventCompleteness:
    """Every event must have required base fields populated."""

    def test_base_fields_present_on_tracked_event(self, student_api, student):
        resp = student_api.post("/api/events/track/", {
            "event_name": "session_started",
            "session_id": "test-session-123",
            "device_type": "desktop",
            "source_page": "/dashboard",
        }, format="json")
        assert resp.status_code == 201

        event = EventLog.objects.get(pk=resp.data["id"])
        assert event.event_name is not None
        assert event.event_version is not None
        assert event.timestamp_utc is not None
        assert event.actor_type is not None
        assert event.request_id is not None

    def test_event_version_default(self, student):
        event = EventLog.objects.create(
            event_name=EventLog.EventName.PAGE_VIEW,
            timestamp_utc=timezone.now(),
            actor=student,
            actor_type=EventLog.ActorType.STUDENT,
        )
        assert event.event_version == "1.0"

    def test_model_has_all_required_fields(self):
        field_names = [f.name for f in EventLog._meta.get_fields()]
        for field in REQUIRED_BASE_FIELDS:
            assert field in field_names, f"EventLog missing required field: {field}"

    def test_learning_event_fields_exist(self):
        field_names = [f.name for f in EventLog._meta.get_fields()]
        learning_fields = [
            "concept", "task", "difficulty_level",
            "attempt_number", "mastery_before", "mastery_after",
            "intervention_reason",
        ]
        for field in learning_fields:
            assert field in field_names, (
                f"EventLog missing learning event field: {field}"
            )


# ---------------------------------------------------------------------------
# OB-02: Event duplication <= 0.1%
# ---------------------------------------------------------------------------


class TestOB02EventDeduplication:
    """Idempotency key must prevent duplicate events."""

    def test_same_idempotency_key_creates_one_event(self, student_api):
        payload = {
            "event_name": "page_view",
            "idempotency_key": "ob02-dedup-test",
        }

        student_api.post("/api/events/track/", payload, format="json")
        student_api.post("/api/events/track/", payload, format="json")

        count = EventLog.objects.filter(
            idempotency_key="ob02-dedup-test",
        ).count()
        assert count == 1

    def test_idempotency_key_field_has_unique_constraint(self):
        field = EventLog._meta.get_field("idempotency_key")
        assert field.unique is True


# ---------------------------------------------------------------------------
# OB-03: Clock skew normalized (server-side timestamp)
# ---------------------------------------------------------------------------


class TestOB03ClockNormalization:
    """timestamp_utc must be server-side; client_timestamp stored separately."""

    def test_timestamp_utc_is_server_side(self, student_api):
        import time
        before = timezone.now()
        time.sleep(0.1)

        resp = student_api.post("/api/events/track/", {
            "event_name": "page_view",
        }, format="json")
        assert resp.status_code == 201

        event = EventLog.objects.get(pk=resp.data["id"])
        assert event.timestamp_utc >= before

    def test_client_timestamp_stored_separately(self, student_api):
        client_ts = "2026-04-16T10:00:00Z"
        resp = student_api.post("/api/events/track/", {
            "event_name": "page_view",
            "client_timestamp": client_ts,
        }, format="json")
        assert resp.status_code == 201

        event = EventLog.objects.get(pk=resp.data["id"])
        assert event.client_timestamp is not None
        assert event.timestamp_utc != event.client_timestamp

    def test_model_has_both_timestamp_fields(self):
        field_names = [f.name for f in EventLog._meta.get_fields()]
        assert "timestamp_utc" in field_names
        assert "client_timestamp" in field_names


# ---------------------------------------------------------------------------
# OB-04: Zero orphan events (actor maps to valid user)
# ---------------------------------------------------------------------------


class TestOB04NoOrphanEvents:
    """Every non-system event must have a valid actor."""

    def test_tracked_event_has_valid_actor(self, student_api, student):
        resp = student_api.post("/api/events/track/", {
            "event_name": "page_view",
        }, format="json")
        assert resp.status_code == 201

        event = EventLog.objects.get(pk=resp.data["id"])
        assert event.actor_id == student.pk
        assert event.actor_type == EventLog.ActorType.STUDENT

    def test_system_event_can_have_null_actor(self):
        event = EventLog.objects.create(
            event_name=EventLog.EventName.SESSION_STARTED,
            timestamp_utc=timezone.now(),
            actor_type=EventLog.ActorType.SYSTEM,
            actor=None,
        )
        assert event.actor is None
        assert event.actor_type == "system"


# ---------------------------------------------------------------------------
# OB-05: Critical events must be BE-confirmed
# ---------------------------------------------------------------------------


class TestOB05CriticalEventConfirmation:
    """
    assessment_completed, micro_task_completed, gv_action_taken
    must NOT be fire-and-forget from FE only. They must have BE confirmation.
    """

    def test_confirmation_required_events_defined(self):
        required = EventLog.CONFIRMATION_REQUIRED_EVENTS
        assert EventLog.EventName.ASSESSMENT_COMPLETED in required
        assert EventLog.EventName.MICRO_TASK_COMPLETED in required
        assert EventLog.EventName.GV_ACTION_TAKEN in required

    def test_confirmed_at_field_exists(self):
        field_names = [f.name for f in EventLog._meta.get_fields()]
        assert "confirmed_at" in field_names

    def test_requires_confirmation_property(self, student):
        event = EventLog(
            event_name=EventLog.EventName.ASSESSMENT_COMPLETED,
            timestamp_utc=timezone.now(),
            actor=student,
            actor_type=EventLog.ActorType.STUDENT,
        )
        assert event.requires_confirmation is True

        page_event = EventLog(
            event_name=EventLog.EventName.PAGE_VIEW,
            timestamp_utc=timezone.now(),
            actor=student,
            actor_type=EventLog.ActorType.STUDENT,
        )
        assert page_event.requires_confirmation is False

    def test_is_learning_event_property(self, student):
        event = EventLog(
            event_name=EventLog.EventName.MICRO_TASK_COMPLETED,
            timestamp_utc=timezone.now(),
            actor=student,
            actor_type=EventLog.ActorType.STUDENT,
        )
        assert event.is_learning_event is True


# ---------------------------------------------------------------------------
# Operations Dashboard verification
# ---------------------------------------------------------------------------


class TestOperationsDashboard:
    """Verify Grafana dashboard JSON has required 9 panels."""

    def test_dashboard_json_exists(self):
        from pathlib import Path
        dashboard_path = Path(__file__).resolve().parents[3] / (
            "infra/grafana/provisioning/dashboards/palp-operations.json"
        )
        assert dashboard_path.exists(), f"Dashboard not found: {dashboard_path}"

    def test_dashboard_has_9_required_panels(self):
        import json
        from pathlib import Path

        dashboard_path = Path(__file__).resolve().parents[3] / (
            "infra/grafana/provisioning/dashboards/palp-operations.json"
        )
        with open(dashboard_path) as f:
            data = json.load(f)

        panels = data.get("panels", [])
        titles = {p["title"] for p in panels}

        required_panels = [
            "App Error Rate",
            "API Latency",
            "Adaptive Decision Latency",
            "Job Success",
            "ETL Data Quality",
            "Event Ingestion",
            "Alert Generation",
            "Export",
            "Backup Freshness",
        ]

        for required in required_panels:
            found = any(required.lower() in t.lower() for t in titles)
            assert found, (
                f"Dashboard missing panel containing '{required}'. "
                f"Found: {titles}"
            )
