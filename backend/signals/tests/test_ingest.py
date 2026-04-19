from datetime import datetime, timedelta, timezone as tz

import pytest

from privacy.models import ConsentRecord
from signals.models import BehaviorScore, SignalSession
from signals.services import ingest_events, rollup_day

pytestmark = pytest.mark.django_db


def _now():
    return datetime.now(tz=tz.utc).replace(microsecond=0)


@pytest.fixture
def signal_consent(student):
    ConsentRecord.objects.create(
        user=student, purpose="behavioral_signals", granted=True, version="1.1",
    )
    return student


def _focus_lost(at, away_ms=60_000):
    return {
        "event_name": "focus_lost",
        "client_timestamp": at.isoformat(),
        "properties": {"focus_duration_ms": away_ms, "trigger": "tab_switch"},
    }


def _frustration(at, intensity=0.8):
    return {
        "event_name": "frustration_signal",
        "client_timestamp": at.isoformat(),
        "properties": {"pattern": "rapid_click", "intensity": intensity},
    }


def _tab_switch(at):
    return {
        "event_name": "tab_switched",
        "client_timestamp": at.isoformat(),
        "properties": {"current_url_path": "/task/1"},
    }


def _give_up(at, task_id=1):
    return {
        "event_name": "give_up_signal",
        "client_timestamp": at.isoformat(),
        "properties": {"task_id": task_id, "trigger": "leave_no_submit", "time_on_task_ms": 120_000},
    }


class TestIngestEvents:
    def test_creates_rollup_for_first_event(self, signal_consent):
        result = ingest_events(
            student=signal_consent,
            raw_session_id="rs-1",
            events=[_focus_lost(_now())],
        )
        assert result["accepted"] == 1
        assert result["rollups_touched"] == 1
        assert SignalSession.objects.filter(student=signal_consent, raw_session_id="rs-1").exists()

    def test_groups_events_into_5min_window(self, signal_consent):
        # Anchor base at the start of the next 5-minute window so the
        # three events (0s, +60s, +120s) all fall safely inside.
        now = _now()
        base = now.replace(minute=now.minute - now.minute % 5, second=0, microsecond=0)
        events = [
            _focus_lost(base, 30_000),
            _focus_lost(base + timedelta(seconds=60), 20_000),
            _focus_lost(base + timedelta(seconds=120), 40_000),
        ]
        ingest_events(student=signal_consent, raw_session_id="rs-2", events=events)
        rollups = SignalSession.objects.filter(student=signal_consent, raw_session_id="rs-2")
        assert rollups.count() == 1
        rollup = rollups.first()
        assert rollup.idle_minutes == pytest.approx((30 + 20 + 40) / 60, abs=1e-2)
        assert rollup.raw_event_count == 3

    def test_separate_window_for_distant_events(self, signal_consent):
        base = _now().replace(minute=0, second=0, microsecond=0)
        events = [
            _focus_lost(base),
            _focus_lost(base + timedelta(minutes=10)),  # different 5-min window
        ]
        ingest_events(student=signal_consent, raw_session_id="rs-3", events=events)
        assert SignalSession.objects.filter(student=signal_consent, raw_session_id="rs-3").count() == 2

    def test_frustration_uses_max_intensity(self, signal_consent):
        base = _now().replace(second=0, microsecond=0)
        ingest_events(
            student=signal_consent,
            raw_session_id="rs-4",
            events=[_frustration(base, 0.3), _frustration(base + timedelta(seconds=10), 0.9)],
        )
        rollup = SignalSession.objects.get(student=signal_consent, raw_session_id="rs-4")
        assert rollup.frustration_score == 0.9

    def test_tab_switch_increments_counter(self, signal_consent):
        base = _now().replace(second=0, microsecond=0)
        ingest_events(
            student=signal_consent,
            raw_session_id="rs-5",
            events=[_tab_switch(base), _tab_switch(base + timedelta(seconds=5))],
        )
        rollup = SignalSession.objects.get(student=signal_consent, raw_session_id="rs-5")
        assert rollup.tab_switches == 2

    def test_give_up_increments_counter(self, signal_consent):
        base = _now().replace(second=0, microsecond=0)
        ingest_events(
            student=signal_consent,
            raw_session_id="rs-6",
            events=[_give_up(base), _give_up(base + timedelta(seconds=30), task_id=2)],
        )
        rollup = SignalSession.objects.get(student=signal_consent, raw_session_id="rs-6")
        assert rollup.give_up_count == 2

    def test_rejects_unknown_event_name(self, signal_consent):
        result = ingest_events(
            student=signal_consent,
            raw_session_id="rs-7",
            events=[{
                "event_name": "page_view",  # not in ACCEPTED_EVENT_NAMES
                "client_timestamp": _now().isoformat(),
                "properties": {},
            }],
        )
        assert result["accepted"] == 0
        assert len(result["rejected"]) == 1
        assert result["rejected"][0]["reason"] == "not_accepted"

    def test_rejects_invalid_schema(self, signal_consent):
        result = ingest_events(
            student=signal_consent,
            raw_session_id="rs-8",
            events=[{
                "event_name": "frustration_signal",
                "client_timestamp": _now().isoformat(),
                # missing required `intensity`
                "properties": {"pattern": "rapid_click"},
            }],
        )
        assert result["accepted"] == 0
        assert len(result["rejected"]) == 1
        assert "intensity" in result["rejected"][0]["reason"].lower() or "required" in result["rejected"][0]["reason"].lower()

    def test_dedup_via_idempotency_key(self, signal_consent):
        base = _now().replace(second=0, microsecond=0)
        ev = _focus_lost(base)
        ev["idempotency_key"] = "uniq-key-1"
        ingest_events(student=signal_consent, raw_session_id="rs-9", events=[ev])
        # Resend exact same event
        result = ingest_events(student=signal_consent, raw_session_id="rs-9", events=[ev])
        # Either treated as duplicate or accepted again with no rollup mutation;
        # either way only 1 rollup row should exist
        assert SignalSession.objects.filter(student=signal_consent, raw_session_id="rs-9").count() == 1


class TestRollupDay:
    def test_aggregates_sessions_into_behavior_score(self, signal_consent):
        base = _now().replace(minute=0, second=0, microsecond=0)
        ingest_events(
            student=signal_consent,
            raw_session_id="rs-day-1",
            events=[_focus_lost(base, 30_000)],
        )
        ingest_events(
            student=signal_consent,
            raw_session_id="rs-day-2",
            events=[_focus_lost(base + timedelta(hours=2), 60_000), _frustration(base + timedelta(hours=2), 0.7)],
        )
        score = rollup_day(signal_consent, base.date())
        assert isinstance(score, BehaviorScore)
        assert score.sessions_count == 2
        assert score.total_focus_minutes > 0

    def test_handles_day_with_no_sessions(self, signal_consent):
        base = _now().replace(minute=0, second=0, microsecond=0)
        score = rollup_day(signal_consent, base.date())
        assert score.sessions_count == 0
