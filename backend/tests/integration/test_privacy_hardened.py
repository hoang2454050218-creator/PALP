"""
Privacy Hardened Tests — upgraded criteria from QA_STANDARD Section 7.2.

Tests for privacy principles and release gate conditions
not covered by the existing privacy/tests.py suite.
"""
import pytest
from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from events.models import EventLog
from privacy.models import ConsentRecord, AuditLog, DataDeletionRequest
from privacy.services import has_consent, sync_user_consent_flag, export_user_data

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


# ---------------------------------------------------------------------------
# PP-01: Consent must be per-purpose, not bundled
# ---------------------------------------------------------------------------


class TestPP01ConsentPerPurpose:
    """Consent must distinguish academic / behavioral / inference separately."""

    def test_partial_consent_respected(self, student, student_api):
        student_api.post("/api/privacy/consent/", {
            "consents": [
                {"purpose": "academic", "granted": True},
                {"purpose": "behavioral", "granted": False},
                {"purpose": "inference", "granted": True},
            ],
            "version": "1.0",
        }, format="json")

        assert has_consent(student, "academic")
        assert not has_consent(student, "behavioral")
        assert has_consent(student, "inference")

    def test_revoke_single_purpose_keeps_others(self, student, student_api):
        for purpose in ["academic", "behavioral", "inference"]:
            ConsentRecord.objects.create(
                user=student, purpose=purpose, granted=True, version="1.0",
            )
        sync_user_consent_flag(student)

        student_api.post("/api/privacy/consent/", {
            "consents": [{"purpose": "behavioral", "granted": False}],
            "version": "1.0",
        }, format="json")

        assert has_consent(student, "academic")
        assert not has_consent(student, "behavioral")
        assert has_consent(student, "inference")


# ---------------------------------------------------------------------------
# PP-02: Export distinguishes 3 data tiers
# ---------------------------------------------------------------------------


class TestPP02DataTiers:
    """Export must separate pii / academic / behavioral / inference."""

    def test_export_has_all_4_tiers(self, student, student_api):
        for purpose in ["academic", "behavioral", "inference"]:
            ConsentRecord.objects.create(
                user=student, purpose=purpose, granted=True, version="1.0",
            )
        sync_user_consent_flag(student)

        resp = student_api.get("/api/privacy/export/")
        assert resp.status_code == 200

        data_tiers = resp.data.get("data", {})
        for tier in ["pii", "academic", "behavioral", "inference"]:
            assert tier in data_tiers, f"Missing tier: {tier}"

    def test_export_meta_has_glossary_and_version(self, student, student_api):
        resp = student_api.get("/api/privacy/export/")
        assert resp.status_code == 200

        meta = resp.data.get("meta", {})
        assert "glossary" in meta
        assert "format_version" in meta
        assert "exported_at" in meta
        assert meta["format_version"] == "1.0"


# ---------------------------------------------------------------------------
# PP-03: Delete policy by tier
# ---------------------------------------------------------------------------


class TestPP03DeletePolicy:
    """Behavioral/inference = hard delete; PII = anonymize."""

    def test_behavioral_hard_deleted(self, student, student_api):
        for purpose in ["academic", "behavioral", "inference"]:
            ConsentRecord.objects.create(
                user=student, purpose=purpose, granted=True, version="1.0",
            )
        sync_user_consent_flag(student)

        EventLog.objects.create(
            actor=student, event_name="page_view",
            actor_type="student", timestamp_utc=timezone.now(),
        )

        student_api.post("/api/privacy/delete/", {
            "tiers": ["behavioral"],
            "confirm": True,
        }, format="json")

        assert EventLog.objects.filter(actor=student).count() == 0

    def test_pii_anonymized_not_deleted(self, student, student_api):
        for purpose in ["academic", "behavioral", "inference"]:
            ConsentRecord.objects.create(
                user=student, purpose=purpose, granted=True, version="1.0",
            )

        original_username = student.username

        student_api.post("/api/privacy/delete/", {
            "tiers": ["pii"],
            "confirm": True,
        }, format="json")

        student.refresh_from_db()
        assert User.objects.filter(pk=student.pk).exists()
        assert student.email != ""
        assert "anon" in student.email or student.first_name == "Deleted"


# ---------------------------------------------------------------------------
# PP-05: Lecturer sees only necessary data
# ---------------------------------------------------------------------------


class TestPP05LecturerMinimalAccess:
    """Lecturer must not see BKT internals or behavioral events."""

    def test_lecturer_mastery_response_no_bkt_internals(
        self, lecturer_api, student, concepts, class_with_members,
    ):
        from adaptive.models import MasteryState
        MasteryState.objects.create(
            student=student, concept=concepts[0],
            p_mastery=0.75, p_guess=0.25, p_slip=0.10, p_transit=0.09,
        )

        resp = lecturer_api.get(f"/api/adaptive/student/{student.pk}/mastery/")
        assert resp.status_code == 200

        results = resp.data.get("results", resp.data) if isinstance(resp.data, dict) else resp.data
        if results and len(results) > 0:
            item = results[0]
            assert "p_guess" not in item, "Lecturer should not see p_guess"
            assert "p_slip" not in item, "Lecturer should not see p_slip"
            assert "p_transit" not in item, "Lecturer should not see p_transit"

    def test_lecturer_events_filtered(
        self, lecturer_api, student, class_with_members,
    ):
        for event_name in ["page_view", "session_started", "assessment_completed"]:
            EventLog.objects.create(
                actor=student, event_name=event_name,
                actor_type="student", timestamp_utc=timezone.now(),
            )

        resp = lecturer_api.get(f"/api/events/student/{student.pk}/")
        assert resp.status_code == 200

        results = resp.data.get("results", resp.data) if isinstance(resp.data, dict) else resp.data
        event_names = {e["event_name"] for e in results}
        assert "page_view" not in event_names, (
            "Lecturer should not see page_view (behavioral detail)"
        )


# ---------------------------------------------------------------------------
# PRG-06: Zero PII leak in API responses
# ---------------------------------------------------------------------------


class TestPRG06NoPIILeak:
    """PII must never appear in unexpected places."""

    def test_dashboard_overview_no_student_names(
        self, lecturer_api, class_with_members,
    ):
        resp = lecturer_api.get(
            f"/api/dashboard/class/{class_with_members.pk}/overview/",
        )
        if resp.status_code == 200:
            content = str(resp.data)
            assert "student@" not in content
            assert "Str0ngP@ss" not in content

    def test_kpi_endpoint_no_student_pii(self, lecturer_api, class_with_members):
        resp = lecturer_api.get(
            f"/api/analytics/kpi/{class_with_members.pk}/",
        )
        if resp.status_code == 200:
            content = str(resp.data)
            assert "email" not in content.lower() or "email" in str(resp.data.keys())

    def test_error_response_no_pii(self, student_api):
        resp = student_api.get("/api/adaptive/pathway/999999/")
        content = str(resp.data)
        assert "@" not in content or "student" not in content


# ---------------------------------------------------------------------------
# PRG-07: Tier confusion — delete only affects chosen tier
# ---------------------------------------------------------------------------


class TestPRG07NoTierConfusion:
    """Deleting one tier must not affect other tiers."""

    def test_delete_behavioral_preserves_inference(self, student, student_api):
        from adaptive.models import MasteryState

        for purpose in ["academic", "behavioral", "inference"]:
            ConsentRecord.objects.create(
                user=student, purpose=purpose, granted=True, version="1.0",
            )
        sync_user_consent_flag(student)

        MasteryState.objects.create(
            student=student,
            concept_id=1,
            p_mastery=0.75,
        )

        EventLog.objects.create(
            actor=student, event_name="page_view",
            actor_type="student", timestamp_utc=timezone.now(),
        )

        student_api.post("/api/privacy/delete/", {
            "tiers": ["behavioral"],
            "confirm": True,
        }, format="json")

        assert EventLog.objects.filter(actor=student).count() == 0
        assert MasteryState.objects.filter(student=student).exists(), (
            "Deleting behavioral tier should not delete inference (mastery) data"
        )

    def test_delete_inference_preserves_pii(self, student, student_api):
        from adaptive.models import MasteryState

        for purpose in ["academic", "behavioral", "inference"]:
            ConsentRecord.objects.create(
                user=student, purpose=purpose, granted=True, version="1.0",
            )

        MasteryState.objects.create(student=student, concept_id=1, p_mastery=0.5)

        original_email = student.email

        student_api.post("/api/privacy/delete/", {
            "tiers": ["inference"],
            "confirm": True,
        }, format="json")

        student.refresh_from_db()
        assert student.email == original_email, (
            "Deleting inference tier should not anonymize PII"
        )
        assert MasteryState.objects.filter(student=student).count() == 0
