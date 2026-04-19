"""Affect service + view tests."""
from __future__ import annotations

import pytest

from affect.models import AffectSnapshot
from affect.services import fuse, ingest_keystroke, ingest_linguistic, recent_for
from privacy.constants import CONSENT_VERSION
from privacy.models import ConsentRecord


pytestmark = pytest.mark.django_db


def _grant_affect(user):
    ConsentRecord.objects.create(
        user=user, purpose="affect_signals", granted=True, version=CONSENT_VERSION,
    )


class TestServices:
    def test_ingest_keystroke_persists(self, student):
        snap = ingest_keystroke(student, {
            "inter_key_intervals_ms": [120] * 30,
            "backspace_ratio": 0.05,
            "burst_count": 12,
            "pause_count": 1,
        })
        assert snap.modality == AffectSnapshot.Modality.KEYSTROKE
        assert AffectSnapshot.objects.filter(student=student).exists()

    def test_ingest_linguistic_persists(self, student):
        snap = ingest_linguistic(student, "Mình thấy hiểu bài rồi, ổn rồi")
        assert snap.modality == AffectSnapshot.Modality.LINGUISTIC
        assert snap.text_length > 0

    def test_fuse_combines_modalities(self, student):
        snap = fuse(
            student,
            keystroke_payload={
                "inter_key_intervals_ms": [100] * 40,
                "backspace_ratio": 0.04,
                "burst_count": 30,
                "pause_count": 0,
            },
            text="Mình thấy hứng thú với bài học này",
        )
        assert snap.modality == AffectSnapshot.Modality.COMBINED
        assert snap.confidence > 0.0
        assert snap.features.get("components")

    def test_recent_for_returns_recent_first(self, student):
        ingest_linguistic(student, "Mình thấy ổn rồi")
        ingest_keystroke(student, {
            "inter_key_intervals_ms": [120] * 30, "backspace_ratio": 0.0,
            "burst_count": 5, "pause_count": 1,
        })
        rows = list(recent_for(student, limit=10))
        assert len(rows) == 2
        assert rows[0].occurred_at >= rows[1].occurred_at


class TestViewsConsentGate:
    def test_blocked_without_consent(self, student, student_api):
        resp = student_api.post(
            "/api/affect/ingest/linguistic/",
            {"text": "Mình thấy hứng thú với bài học này"},
            format="json",
        )
        assert resp.status_code in (403, 401)

    def test_works_with_consent(self, student, student_api):
        _grant_affect(student)
        resp = student_api.post(
            "/api/affect/ingest/linguistic/",
            {"text": "Mình thấy hứng thú với bài học này"},
            format="json",
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["modality"] == "linguistic"

    def test_recent_endpoint(self, student, student_api):
        _grant_affect(student)
        ingest_linguistic(student, "Mình thấy hiểu bài rồi")
        resp = student_api.get("/api/affect/me/recent/")
        assert resp.status_code == 200
        body = resp.json()
        rows = body["results"] if isinstance(body, dict) else body
        assert isinstance(rows, list)
        assert len(rows) >= 1

    def test_keystroke_ingest_passes_consent(self, student, student_api):
        _grant_affect(student)
        resp = student_api.post(
            "/api/affect/ingest/keystroke/",
            {
                "metrics": {
                    "inter_key_intervals_ms": [120] * 30,
                    "backspace_ratio": 0.05,
                    "burst_count": 12,
                    "pause_count": 1,
                }
            },
            format="json",
        )
        assert resp.status_code == 201
