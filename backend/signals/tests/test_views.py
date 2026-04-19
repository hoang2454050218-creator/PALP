from datetime import datetime, timezone as tz

import pytest

from privacy.models import ConsentRecord

pytestmark = pytest.mark.django_db


def _ts():
    return datetime.now(tz=tz.utc).isoformat()


@pytest.fixture
def consented_student(student):
    ConsentRecord.objects.create(
        user=student, purpose="behavioral_signals", granted=True, version="1.1",
    )
    # Also add other consents needed by middleware-level gates (none for /api/signals/)
    return student


@pytest.fixture
def consented_student_api(consented_student, student_api):
    return student_api


class TestSignalIngestView:
    def test_authenticated_with_consent_returns_202(self, consented_student_api):
        resp = consented_student_api.post(
            "/api/signals/ingest/",
            data={
                "raw_session_id": "rs-1",
                "events": [
                    {
                        "event_name": "focus_lost",
                        "client_timestamp": _ts(),
                        "properties": {"focus_duration_ms": 30000, "trigger": "tab_switch"},
                    },
                ],
            },
            format="json",
        )
        assert resp.status_code == 202
        assert resp.data["accepted"] == 1

    def test_anon_rejected(self, anon_api):
        resp = anon_api.post(
            "/api/signals/ingest/",
            data={"raw_session_id": "rs", "events": [{"event_name": "focus_lost", "client_timestamp": _ts(), "properties": {"focus_duration_ms": 0, "trigger": "tab_switch"}}]},
            format="json",
        )
        assert resp.status_code in (401, 403)

    def test_student_without_consent_403(self, student_api):
        # No ConsentRecord -> permission denied
        resp = student_api.post(
            "/api/signals/ingest/",
            data={"raw_session_id": "rs", "events": [{"event_name": "focus_lost", "client_timestamp": _ts(), "properties": {"focus_duration_ms": 0, "trigger": "tab_switch"}}]},
            format="json",
        )
        assert resp.status_code == 403

    def test_lecturer_rejected_even_with_consent(self, lecturer_api, lecturer):
        ConsentRecord.objects.create(user=lecturer, purpose="behavioral_signals", granted=True, version="1.1")
        resp = lecturer_api.post(
            "/api/signals/ingest/",
            data={"raw_session_id": "rs", "events": [{"event_name": "focus_lost", "client_timestamp": _ts(), "properties": {"focus_duration_ms": 0, "trigger": "tab_switch"}}]},
            format="json",
        )
        assert resp.status_code == 403  # only students

    def test_empty_batch_rejected(self, consented_student_api):
        resp = consented_student_api.post(
            "/api/signals/ingest/",
            data={"raw_session_id": "rs", "events": []},
            format="json",
        )
        assert resp.status_code == 400

    def test_oversize_batch_rejected(self, consented_student_api):
        events = [
            {
                "event_name": "tab_switched",
                "client_timestamp": _ts(),
                "properties": {},
            }
            for _ in range(201)
        ]
        resp = consented_student_api.post(
            "/api/signals/ingest/",
            data={"raw_session_id": "rs", "events": events},
            format="json",
        )
        assert resp.status_code == 400


class TestMySignalsView:
    def test_returns_own_sessions(self, consented_student_api):
        # Ingest first
        consented_student_api.post(
            "/api/signals/ingest/",
            data={
                "raw_session_id": "rs-mine",
                "events": [
                    {"event_name": "focus_lost", "client_timestamp": _ts(), "properties": {"focus_duration_ms": 30000, "trigger": "tab_switch"}},
                ],
            },
            format="json",
        )
        resp = consented_student_api.get("/api/signals/my/")
        assert resp.status_code == 200
        assert resp.data["count"] >= 1

    def test_anon_rejected(self, anon_api):
        resp = anon_api.get("/api/signals/my/")
        assert resp.status_code in (401, 403)
