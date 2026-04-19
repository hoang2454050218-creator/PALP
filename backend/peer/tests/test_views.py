"""HTTP integration tests for the Peer Engine views."""
from __future__ import annotations

import pytest

from adaptive.models import MasteryState
from peer.models import PeerCohort, PeerConsent, ReciprocalPeerMatch
from privacy.constants import CONSENT_VERSION
from privacy.models import ConsentRecord

pytestmark = pytest.mark.django_db


def _grant(student, *purposes):
    for p in purposes:
        ConsentRecord.objects.create(
            user=student, purpose=p, granted=True, version=CONSENT_VERSION,
        )


# ---------------------------------------------------------------------------
# Consent
# ---------------------------------------------------------------------------

class TestPeerConsentEndpoint:
    def test_get_creates_default_row(self, student_api):
        resp = student_api.get("/api/peer/consent/")
        assert resp.status_code == 200
        assert resp.data["frontier_mode"] is True
        assert resp.data["peer_comparison"] is False
        assert resp.data["peer_teaching"] is False

    def test_patch_records_consent_version(self, student_api, student):
        resp = student_api.patch(
            "/api/peer/consent/",
            {"peer_comparison": True},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["peer_comparison"] is True
        assert ConsentRecord.objects.filter(
            user=student, purpose="peer_comparison", granted=True,
        ).exists()

    def test_patch_lecturer_rejected(self, lecturer_api):
        resp = lecturer_api.patch(
            "/api/peer/consent/",
            {"peer_comparison": True},
            format="json",
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Frontier (no consent required)
# ---------------------------------------------------------------------------

class TestFrontierEndpoint:
    def test_returns_zero_payload_for_brand_new_student(self, student_api):
        resp = student_api.get("/api/peer/frontier/")
        assert resp.status_code == 200
        assert resp.data["delta"] == 0.0
        assert resp.data["concepts_progressed"] == []

    def test_returns_progress_summary(self, student_api, student, concepts):
        c1 = concepts[0]
        MasteryState.objects.create(
            student=student, concept=c1, p_mastery=0.6, attempt_count=2,
        )
        resp = student_api.get("/api/peer/frontier/")
        assert resp.status_code == 200
        assert resp.data["current_avg_mastery"] > 0


# ---------------------------------------------------------------------------
# Benchmark — consent required by middleware
# ---------------------------------------------------------------------------

class TestBenchmarkEndpoint:
    def test_blocked_without_consent(self, student_api):
        resp = student_api.get("/api/peer/benchmark/")
        assert resp.status_code == 403

    def test_allowed_with_consent_returns_unavailable_when_no_cohort(
        self, student_api, student,
    ):
        _grant(student, "peer_comparison")
        resp = student_api.get("/api/peer/benchmark/")
        assert resp.status_code == 200
        assert resp.data["available"] is False
        assert resp.data["reason"] == "cohort_not_assigned"


# ---------------------------------------------------------------------------
# Buddy
# ---------------------------------------------------------------------------

class TestBuddyEndpoints:
    def test_find_blocked_without_consent(self, student_api):
        resp = student_api.post("/api/peer/buddy/find/")
        assert resp.status_code == 403

    def test_find_returns_none_message_when_no_match(self, student_api, student):
        _grant(student, "peer_teaching")
        resp = student_api.post("/api/peer/buddy/find/")
        assert resp.status_code == 200
        assert resp.data["match"] is None
        assert "Chưa tìm" in resp.data["message"]

    def test_find_creates_match_when_reciprocal_pair_exists(
        self,
        student_api,
        student,
        student_b,
        class_with_members,
        concepts,
    ):
        _grant(student, "peer_teaching")
        _grant(student_b, "peer_teaching")
        cohort = PeerCohort.objects.create(
            student_class=class_with_members,
            ability_band_label="band_0",
            members_count=2,
        )
        cohort.members.set([student, student_b])

        c1, c2, _ = concepts
        for st, vals in [(student, [0.9, 0.2]), (student_b, [0.2, 0.9])]:
            for c, v in zip([c1, c2], vals):
                MasteryState.objects.update_or_create(
                    student=st, concept=c,
                    defaults={"p_mastery": v, "attempt_count": 5},
                )

        resp = student_api.post("/api/peer/buddy/find/")
        assert resp.status_code == 200
        assert resp.data["match"] is not None
        assert resp.data["match"]["partner"]["id"] == student_b.id
        # Anti-rank rule: response must NOT expose absolute scores.
        match_payload = resp.data["match"]
        assert "p_mastery" not in match_payload
        assert "rank" not in match_payload

    def test_respond_archive_changes_status(
        self, student_api, student, student_b, concepts, class_with_members,
    ):
        _grant(student, "peer_teaching")
        cohort = PeerCohort.objects.create(
            student_class=class_with_members,
            ability_band_label="band_0",
            members_count=2,
        )
        cohort.members.set([student, student_b])
        match = ReciprocalPeerMatch.objects.create(
            cohort=cohort,
            student_a=student,
            student_b=student_b,
            concept_a_to_b=concepts[0],
            concept_b_to_a=concepts[1],
            compatibility_score=0.5,
        )
        resp = student_api.post(
            f"/api/peer/buddy/{match.id}/respond/",
            {"action": "archive"},
            format="json",
        )
        assert resp.status_code == 200
        match.refresh_from_db()
        assert match.status == ReciprocalPeerMatch.Status.ARCHIVED


# ---------------------------------------------------------------------------
# Teaching session
# ---------------------------------------------------------------------------

class TestTeachingSessionStart:
    def test_blocked_when_match_not_active(
        self, student_api, student, student_b, concepts, class_with_members,
    ):
        _grant(student, "peer_teaching")
        match = ReciprocalPeerMatch.objects.create(
            student_a=student, student_b=student_b,
            concept_a_to_b=concepts[0], concept_b_to_a=concepts[1],
            compatibility_score=0.5,
        )
        resp = student_api.post(
            f"/api/peer/teaching-session/{match.id}/start/"
        )
        assert resp.status_code == 400

    def test_creates_session_when_match_active(
        self, student_api, student, student_b, concepts, class_with_members,
    ):
        _grant(student, "peer_teaching")
        match = ReciprocalPeerMatch.objects.create(
            student_a=student, student_b=student_b,
            concept_a_to_b=concepts[0], concept_b_to_a=concepts[1],
            compatibility_score=0.5,
            status=ReciprocalPeerMatch.Status.ACTIVE,
        )
        resp = student_api.post(
            f"/api/peer/teaching-session/{match.id}/start/"
        )
        assert resp.status_code == 201
        assert resp.data["match"] == match.id


# ---------------------------------------------------------------------------
# Herd clusters — lecturer side
# ---------------------------------------------------------------------------

class TestHerdClusterEndpoint:
    def test_student_cannot_list(self, student_api):
        resp = student_api.get("/api/peer/herd-clusters/")
        assert resp.status_code == 403

    def test_lecturer_lists_only_assigned_classes(
        self,
        lecturer_api,
        lecturer_other_api,
        class_with_members,
        student,
        student_b,
    ):
        from peer.models import HerdCluster
        cluster = HerdCluster.objects.create(
            student_class=class_with_members,
            severity="medium",
            mean_risk_score=72.0,
        )
        cluster.members.set([student, student_b])

        resp_assigned = lecturer_api.get("/api/peer/herd-clusters/")
        resp_other = lecturer_other_api.get("/api/peer/herd-clusters/")
        assert resp_assigned.status_code == 200
        assert resp_other.status_code == 200
        assert len(resp_assigned.data["clusters"]) == 1
        assert resp_other.data["clusters"] == []
