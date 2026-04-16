import logging

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import (
    User, StudentClass, ClassMembership, LecturerClassAssignment,
)
from adaptive.models import MasteryState, TaskAttempt, ContentIntervention, StudentPathway
from assessment.models import AssessmentSession, LearnerProfile
from curriculum.models import Course, Concept
from dashboard.models import Alert
from events.models import EventLog
from wellbeing.models import WellbeingNudge

from .models import AuditLog, ConsentRecord, DataDeletionRequest, PrivacyIncident
from .services import (
    delete_user_data,
    enforce_retention,
    export_user_data,
    get_consent_status,
    has_consent,
    sync_user_consent_flag,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def student(db):
    return User.objects.create_user(
        username="privacy_student", password="Str0ngP@ss!",
        role=User.Role.STUDENT, student_id="22KT9999",
        first_name="Nguyen", last_name="Test",
        email="student@test.palp",
        phone="0901234567",
    )


@pytest.fixture
def lecturer(db):
    return User.objects.create_user(
        username="privacy_lecturer", password="Str0ngP@ss!",
        role=User.Role.LECTURER,
        first_name="Le", last_name="GV",
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="privacy_admin", password="Str0ngP@ss!",
        role=User.Role.ADMIN,
    )


@pytest.fixture
def course(db):
    return Course.objects.create(code="PVT", name="Privacy Test Course")


@pytest.fixture
def concepts(course):
    c1 = Concept.objects.create(course=course, code="C1", name="Concept 1", order=1)
    c2 = Concept.objects.create(course=course, code="C2", name="Concept 2", order=2)
    return [c1, c2]


@pytest.fixture
def student_class(db):
    return StudentClass.objects.create(name="PVT-01", academic_year="2025-2026")


@pytest.fixture
def class_with_members(student, lecturer, student_class):
    ClassMembership.objects.create(student=student, student_class=student_class)
    LecturerClassAssignment.objects.create(lecturer=lecturer, student_class=student_class)
    return student_class


@pytest.fixture
def student_api(student):
    client = APIClient()
    client.force_authenticate(user=student)
    return client


@pytest.fixture
def lecturer_api(lecturer):
    client = APIClient()
    client.force_authenticate(user=lecturer)
    return client


@pytest.fixture
def admin_api(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def anon_api():
    return APIClient()


def _grant_all_consents(user):
    for purpose in ConsentRecord.Purpose.values:
        ConsentRecord.objects.create(
            user=user, purpose=purpose, granted=True, version="1.0",
        )
    sync_user_consent_flag(user)


# ====================================================================
# GATE 1: 100% Consent Flow
# ====================================================================

@pytest.mark.django_db
class TestConsentFlow:

    def test_grant_consent_per_purpose(self, student_api, student):
        resp = student_api.post("/api/privacy/consent/", {
            "consents": [
                {"purpose": "academic", "granted": True},
                {"purpose": "behavioral", "granted": True},
                {"purpose": "inference", "granted": True},
            ],
            "version": "1.0",
        }, format="json")
        assert resp.status_code == 200

        records = ConsentRecord.objects.filter(user=student)
        assert records.count() == 3
        assert all(r.granted for r in records)

    def test_revoke_consent(self, student_api, student):
        _grant_all_consents(student)

        resp = student_api.post("/api/privacy/consent/", {
            "consents": [{"purpose": "behavioral", "granted": False}],
            "version": "1.0",
        }, format="json")
        assert resp.status_code == 200

        assert not has_consent(student, "behavioral")
        assert has_consent(student, "academic")

    def test_re_grant_consent(self, student_api, student):
        ConsentRecord.objects.create(
            user=student, purpose="behavioral", granted=True, version="1.0",
        )
        ConsentRecord.objects.create(
            user=student, purpose="behavioral", granted=False, version="1.0",
        )
        assert not has_consent(student, "behavioral")

        student_api.post("/api/privacy/consent/", {
            "consents": [{"purpose": "behavioral", "granted": True}],
            "version": "1.0",
        }, format="json")
        assert has_consent(student, "behavioral")

    def test_consent_history_preserved(self, student_api, student):
        for granted in [True, False, True]:
            student_api.post("/api/privacy/consent/", {
                "consents": [{"purpose": "academic", "granted": granted}],
                "version": "1.0",
            }, format="json")

        records = ConsentRecord.objects.filter(user=student, purpose="academic")
        assert records.count() == 3

        resp = student_api.get("/api/privacy/consent/history/")
        assert resp.status_code == 200
        assert len(resp.data) >= 3

    def test_get_consent_status(self, student_api, student):
        _grant_all_consents(student)
        resp = student_api.get("/api/privacy/consent/")
        assert resp.status_code == 200
        purposes = {item["purpose"] for item in resp.data}
        assert purposes == {"academic", "behavioral", "inference"}

    def test_consent_sync_to_user_flag(self, student):
        _grant_all_consents(student)
        student.refresh_from_db()
        assert student.consent_given is True

        ConsentRecord.objects.create(
            user=student, purpose="inference", granted=False, version="1.0",
        )
        sync_user_consent_flag(student)
        student.refresh_from_db()
        assert student.consent_given is False

    def test_duplicate_purpose_rejected(self, student_api):
        resp = student_api.post("/api/privacy/consent/", {
            "consents": [
                {"purpose": "academic", "granted": True},
                {"purpose": "academic", "granted": False},
            ],
            "version": "1.0",
        }, format="json")
        assert resp.status_code == 400

    def test_unauthenticated_cannot_consent(self, anon_api):
        resp = anon_api.post("/api/privacy/consent/", {
            "consents": [{"purpose": "academic", "granted": True}],
        }, format="json")
        assert resp.status_code == 401


# ====================================================================
# GATE 2: 100% Export Flow
# ====================================================================

@pytest.mark.django_db
class TestExportFlow:

    def test_export_returns_all_tiers(self, student_api, student, course, concepts):
        _grant_all_consents(student)

        MasteryState.objects.create(
            student=student, concept=concepts[0], p_mastery=0.75,
        )

        resp = student_api.get("/api/privacy/export/")
        assert resp.status_code == 200
        data = resp.data

        assert "meta" in data
        assert "data" in data
        assert "glossary" in data["meta"]
        assert "exported_at" in data["meta"]
        assert data["meta"]["user_id"] == student.id

        assert "pii" in data["data"]
        assert "academic" in data["data"]
        assert "behavioral" in data["data"]
        assert "inference" in data["data"]

    def test_export_contains_glossary(self, student_api, student):
        resp = student_api.get("/api/privacy/export/")
        assert resp.status_code == 200
        glossary = resp.data["meta"]["glossary"]
        assert "p_mastery" in glossary
        assert "email" in glossary

    def test_export_contains_pii(self, student_api, student):
        resp = student_api.get("/api/privacy/export/")
        assert resp.status_code == 200
        pii = resp.data["data"]["pii"]["user"]
        assert pii["email"] == "student@test.palp"
        assert pii["student_id"] == "22KT9999"

    def test_student_cannot_export_other_student(self, student_api, student):
        other = User.objects.create_user(
            username="other_student", password="Str0ngP@ss!",
            role=User.Role.STUDENT,
        )
        resp = student_api.get(f"/api/privacy/export/?user_id={other.id}")
        pii = resp.data["data"]["pii"]["user"]
        assert pii["id"] == student.id

    def test_admin_can_export_any_student(self, admin_api, student):
        resp = admin_api.get(f"/api/privacy/export/?user_id={student.id}")
        assert resp.status_code == 200
        assert resp.data["meta"]["user_id"] == student.id

    def test_export_creates_audit_log(self, student_api, student):
        student_api.get("/api/privacy/export/")
        assert AuditLog.objects.filter(
            actor=student, action=AuditLog.Action.EXPORT
        ).exists()


# ====================================================================
# GATE 3: 100% Delete/Anonymize Flow
# ====================================================================

@pytest.mark.django_db
class TestDeleteAnonymizeFlow:

    def test_hard_delete_behavioral(self, student, course, concepts):
        MasteryState.objects.create(student=student, concept=concepts[0])
        EventLog.objects.create(
            actor=student, event_name="page_view",
            actor_type="student", timestamp_utc=timezone.now(),
        )

        summary = delete_user_data(student, ["behavioral"])
        assert EventLog.objects.filter(actor=student).count() == 0
        assert "behavioral" in summary

    def test_hard_delete_inference(self, student, course, concepts):
        MasteryState.objects.create(student=student, concept=concepts[0])

        summary = delete_user_data(student, ["inference"])
        assert MasteryState.objects.filter(student=student).count() == 0
        assert "inference" in summary

    def test_anonymize_pii(self, student):
        original_email = student.email

        delete_user_data(student, ["pii"])
        student.refresh_from_db()

        assert student.email != original_email
        assert "anon.palp" in student.email
        assert student.first_name == "Deleted"
        assert student.student_id == ""
        assert student.phone == ""

    def test_delete_requires_confirm(self, student_api):
        resp = student_api.post("/api/privacy/delete/", {
            "tiers": ["behavioral"],
            "confirm": False,
        }, format="json")
        assert resp.status_code == 400

    def test_delete_creates_deletion_request(self, student_api, student):
        resp = student_api.post("/api/privacy/delete/", {
            "tiers": ["behavioral"],
            "confirm": True,
        }, format="json")
        assert resp.status_code == 200

        req = DataDeletionRequest.objects.filter(user=student).first()
        assert req is not None
        assert req.status == DataDeletionRequest.RequestStatus.COMPLETED

    def test_delete_creates_audit_log(self, student, course, concepts):
        MasteryState.objects.create(student=student, concept=concepts[0])
        delete_user_data(student, ["inference"])
        assert AuditLog.objects.filter(
            action=AuditLog.Action.DELETE, target_user=student,
        ).exists()

    def test_deletion_requests_list(self, student_api, student):
        DataDeletionRequest.objects.create(
            user=student, tiers=["behavioral"],
            status=DataDeletionRequest.RequestStatus.COMPLETED,
        )
        resp = student_api.get("/api/privacy/delete/requests/")
        assert resp.status_code == 200
        assert len(resp.data) >= 1


# ====================================================================
# GATE 4: 100% RBAC
# ====================================================================

@pytest.mark.django_db
class TestRBAC:

    def test_lecturer_sees_filtered_events(
        self, lecturer_api, student, lecturer, class_with_members,
    ):
        for event_name in ["page_view", "wellbeing_nudge_shown", "assessment_completed"]:
            EventLog.objects.create(
                actor=student, event_name=event_name,
                actor_type="student", timestamp_utc=timezone.now(),
            )

        resp = lecturer_api.get(f"/api/events/student/{student.id}/")
        assert resp.status_code == 200

        event_names = {e["event_name"] for e in resp.data.get("results", resp.data)}
        assert "page_view" not in event_names
        assert "wellbeing_nudge_shown" not in event_names

    def test_lecturer_sees_filtered_mastery(
        self, lecturer_api, student, lecturer, course, concepts, class_with_members,
    ):
        MasteryState.objects.create(
            student=student, concept=concepts[0],
            p_mastery=0.75, p_guess=0.25, p_slip=0.10, p_transit=0.09,
        )

        resp = lecturer_api.get(f"/api/adaptive/student/{student.id}/mastery/")
        assert resp.status_code == 200

        results = resp.data.get("results", resp.data)
        if results:
            item = results[0]
            assert "p_mastery" in item
            assert "p_guess" not in item
            assert "p_slip" not in item
            assert "p_transit" not in item

    def test_student_cannot_see_other_student_data(self, student_api):
        other = User.objects.create_user(
            username="other", password="Str0ngP@ss!", role=User.Role.STUDENT,
        )
        resp = student_api.get(f"/api/events/student/{other.id}/")
        assert resp.status_code == 403

    def test_admin_can_view_incidents(self, admin_api):
        resp = admin_api.get("/api/privacy/incidents/")
        assert resp.status_code == 200

    def test_student_cannot_view_incidents(self, student_api):
        resp = student_api.get("/api/privacy/incidents/")
        assert resp.status_code == 403

    def test_consent_gate_blocks_without_consent(self, student_api, student):
        assert not has_consent(student, "behavioral")

        resp = student_api.post("/api/events/track/", {
            "event_name": "page_view",
        }, format="json")
        assert resp.status_code == 403
        assert "consent_required" in resp.data

    def test_consent_gate_allows_with_consent(self, student_api, student):
        _grant_all_consents(student)

        resp = student_api.post("/api/events/track/", {
            "event_name": "page_view",
            "session_id": "test-session",
        }, format="json")
        assert resp.status_code in (200, 201)


# ====================================================================
# GATE 5: 100% Audit Trail
# ====================================================================

@pytest.mark.django_db
class TestAuditTrail:

    def test_consent_change_logged(self, student_api, student):
        student_api.post("/api/privacy/consent/", {
            "consents": [{"purpose": "academic", "granted": True}],
            "version": "1.0",
        }, format="json")

        assert AuditLog.objects.filter(
            actor=student,
            action=AuditLog.Action.CONSENT_CHANGE,
        ).exists()

    def test_export_logged(self, student_api, student):
        student_api.get("/api/privacy/export/")
        assert AuditLog.objects.filter(
            actor=student,
            action=AuditLog.Action.EXPORT,
        ).exists()

    def test_delete_logged(self, student_api, student):
        student_api.post("/api/privacy/delete/", {
            "tiers": ["behavioral"],
            "confirm": True,
        }, format="json")

        assert AuditLog.objects.filter(
            action=AuditLog.Action.DELETE,
            target_user=student,
        ).exists()

    def test_incident_logged(self, admin_api, admin_user):
        admin_api.post("/api/privacy/incidents/", {
            "severity": "high",
            "title": "Test incident",
            "description": "PII leak detected",
            "affected_user_count": 5,
        }, format="json")

        assert AuditLog.objects.filter(
            actor=admin_user,
            action=AuditLog.Action.INCIDENT,
        ).exists()

    def test_student_sees_own_audit_log(self, student_api, student):
        AuditLog.objects.create(
            actor=student,
            action=AuditLog.Action.EXPORT,
            target_user=student,
            resource="test",
        )

        resp = student_api.get("/api/privacy/audit-log/")
        assert resp.status_code == 200
        assert len(resp.data) >= 1

    def test_admin_sees_all_audit_logs(self, admin_api, student):
        AuditLog.objects.create(
            actor=student,
            action=AuditLog.Action.EXPORT,
            target_user=student,
            resource="test",
        )

        resp = admin_api.get("/api/privacy/audit-log/")
        assert resp.status_code == 200


# ====================================================================
# GATE 6: 0 PII Leaks
# ====================================================================

@pytest.mark.django_db
class TestPIIScrubbing:

    def test_log_filter_scrubs_email(self):
        from .middleware import PIIScrubLogFilter

        filt = PIIScrubLogFilter()
        record = logging.LogRecord(
            "test", logging.INFO, "", 0,
            "User email is student@test.com", (), None,
        )
        filt.filter(record)
        assert "student@test.com" not in record.msg
        assert "[EMAIL]" in record.msg

    def test_log_filter_scrubs_phone(self):
        from .middleware import PIIScrubLogFilter

        filt = PIIScrubLogFilter()
        record = logging.LogRecord(
            "test", logging.INFO, "", 0,
            "User phone is 0901234567", (), None,
        )
        filt.filter(record)
        assert "0901234567" not in record.msg
        assert "[PHONE]" in record.msg

    def test_log_filter_scrubs_student_id(self):
        from .middleware import PIIScrubLogFilter

        filt = PIIScrubLogFilter()
        record = logging.LogRecord(
            "test", logging.INFO, "", 0,
            "Student ID: 22000123", (), None,
        )
        filt.filter(record)
        assert "22000123" not in record.msg

    def test_exception_handler_scrubs_pii(self):
        from .exception_handler import _scrub_string

        text = "Error for user test@email.com"
        scrubbed = _scrub_string(text)
        assert "test@email.com" not in scrubbed
        assert "[EMAIL]" in scrubbed

    def test_sentry_scrub_function(self):
        import importlib
        production_settings = importlib.import_module("palp.settings.production")
        scrub = production_settings._scrub_pii_from_event

        event = {
            "request": {
                "data": {"email": "test@test.com", "password": "secret"},
                "cookies": "session=abc",
                "headers": {"Authorization": "Bearer xyz"},
            },
            "user": {
                "email": "test@test.com",
                "username": "testuser",
            },
        }
        result = scrub(event, None)
        assert result["request"]["data"] == "[REDACTED]"
        assert result["request"]["cookies"] == "[REDACTED]"
        assert result["user"]["email"] == "[REDACTED]"


# ====================================================================
# Retention Enforcement
# ====================================================================

@pytest.mark.django_db
class TestRetention:

    def test_retention_deletes_old_behavioral(self, student, course, concepts):
        from datetime import timedelta

        old_event = EventLog.objects.create(
            actor=student, event_name="page_view",
            actor_type="student",
            timestamp_utc=timezone.now() - timedelta(days=400),
        )
        new_event = EventLog.objects.create(
            actor=student, event_name="page_view",
            actor_type="student",
            timestamp_utc=timezone.now(),
        )

        enforce_retention()

        assert not EventLog.objects.filter(id=old_event.id).exists()
        assert EventLog.objects.filter(id=new_event.id).exists()


# ====================================================================
# Incident Response
# ====================================================================

@pytest.mark.django_db
class TestIncidentResponse:

    def test_create_incident(self, admin_api):
        resp = admin_api.post("/api/privacy/incidents/", {
            "severity": "critical",
            "title": "PII breach in logs",
            "description": "Student emails found in error logs.",
            "affected_user_count": 50,
            "affected_data_tiers": ["pii"],
        }, format="json")
        assert resp.status_code == 201

        incident = PrivacyIncident.objects.first()
        assert incident is not None
        assert incident.is_within_sla

    def test_incident_sla_deadline_set(self, admin_api):
        admin_api.post("/api/privacy/incidents/", {
            "severity": "high",
            "title": "Test",
            "description": "Test incident",
        }, format="json")

        incident = PrivacyIncident.objects.first()
        delta = incident.sla_deadline - incident.created_at
        assert 47 * 3600 <= delta.total_seconds() <= 49 * 3600

    def test_student_cannot_create_incident(self, student_api):
        resp = student_api.post("/api/privacy/incidents/", {
            "severity": "low",
            "title": "Test",
            "description": "Test",
        }, format="json")
        assert resp.status_code == 403
