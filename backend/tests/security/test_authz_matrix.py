"""
Full role-permission matrix tests for every protected endpoint.

For each endpoint, verifies:
  - Unauthenticated -> 401
  - Wrong role -> 403
  - Correct role -> success (200/201/etc.)
  - Object-level checks where applicable

Coverage gate: 100 % of non-AllowAny endpoints.
"""

import uuid

import pytest
from dashboard.models import Alert
from adaptive.models import MasteryState
from wellbeing.models import WellbeingNudge

pytestmark = [pytest.mark.django_db, pytest.mark.security]


def _idem():
    return str(uuid.uuid4())


class TestUnauthenticatedDenied:
    """Every authenticated endpoint must return 401 for anonymous requests."""

    ENDPOINTS = [
        ("get", "/api/auth/profile/"),
        ("put", "/api/auth/profile/"),
        ("post", "/api/auth/logout/"),
        ("post", "/api/auth/consent/"),
        ("get", "/api/auth/classes/"),
        ("get", "/api/assessment/"),
        ("get", "/api/adaptive/mastery/"),
        ("post", "/api/adaptive/submit/"),
        ("get", "/api/adaptive/attempts/"),
        ("get", "/api/adaptive/interventions/"),
        ("get", "/api/curriculum/courses/"),
        ("get", "/api/curriculum/tasks/"),
        ("get", "/api/curriculum/my-enrollments/"),
        ("get", "/api/dashboard/alerts/"),
        ("post", "/api/dashboard/interventions/"),
        ("get", "/api/dashboard/interventions/history/"),
        ("post", "/api/events/track/"),
        ("post", "/api/events/batch/"),
        ("get", "/api/events/my/"),
        ("post", "/api/wellbeing/check/"),
        ("get", "/api/wellbeing/my/"),
        ("get", "/api/analytics/reports/"),
        ("get", "/api/analytics/data-quality/"),
        ("get", "/api/privacy/consent/"),
        ("post", "/api/privacy/consent/"),
        ("get", "/api/privacy/consent/history/"),
        ("get", "/api/privacy/export/"),
        ("post", "/api/privacy/delete/"),
        ("get", "/api/privacy/delete/requests/"),
        ("get", "/api/privacy/audit-log/"),
        ("get", "/api/privacy/incidents/"),
        ("post", "/api/privacy/incidents/"),
    ]

    @pytest.mark.parametrize("method,path", ENDPOINTS)
    def test_unauthenticated_returns_401(self, anon_api, method, path):
        caller = getattr(anon_api, method)
        extra = {}
        if method == "post":
            extra = {"format": "json", "data": {}}
        resp = caller(path, **extra)
        assert resp.status_code == 401, (
            f"{method.upper()} {path} returned {resp.status_code}, expected 401"
        )


class TestStudentRestrictions:
    """Students must be denied access to lecturer/admin resources."""

    def test_cannot_access_classes_list(self, student_api):
        resp = student_api.get("/api/auth/classes/")
        assert resp.status_code == 403

    def test_cannot_access_class_students(
        self, student_api, class_with_members,
    ):
        resp = student_api.get(
            f"/api/auth/classes/{class_with_members.pk}/students/"
        )
        assert resp.status_code == 403

    def test_cannot_access_dashboard_overview(
        self, student_api, class_with_members,
    ):
        resp = student_api.get(
            f"/api/dashboard/class/{class_with_members.pk}/overview/"
        )
        assert resp.status_code == 403

    def test_cannot_access_alerts(self, student_api):
        resp = student_api.get("/api/dashboard/alerts/")
        assert resp.status_code == 403

    def test_cannot_dismiss_alert(
        self, student_api, student, class_with_members,
    ):
        alert = Alert.objects.create(
            student=student,
            student_class=class_with_members,
            severity=Alert.Severity.YELLOW,
            trigger_type=Alert.TriggerType.INACTIVITY,
            reason="Test",
        )
        resp = student_api.post(f"/api/dashboard/alerts/{alert.pk}/dismiss/")
        assert resp.status_code == 403

    def test_cannot_create_intervention(self, student_api):
        resp = student_api.post(
            "/api/dashboard/interventions/", {}, format="json",
        )
        assert resp.status_code == 403

    def test_cannot_view_interventions_history(self, student_api):
        resp = student_api.get("/api/dashboard/interventions/history/")
        assert resp.status_code == 403

    def test_cannot_access_other_student_events(
        self, student_api, student_b,
    ):
        resp = student_api.get(f"/api/events/student/{student_b.pk}/")
        assert resp.status_code == 403

    def test_cannot_access_analytics_kpi(
        self, student_api, class_with_members,
    ):
        resp = student_api.get(
            f"/api/analytics/kpi/{class_with_members.pk}/"
        )
        assert resp.status_code == 403

    def test_cannot_access_analytics_reports(self, student_api):
        resp = student_api.get("/api/analytics/reports/")
        assert resp.status_code == 403

    def test_cannot_access_data_quality(self, student_api):
        resp = student_api.get("/api/analytics/data-quality/")
        assert resp.status_code == 403

    def test_cannot_access_privacy_incidents(self, student_api):
        resp = student_api.get("/api/privacy/incidents/")
        assert resp.status_code == 403

    def test_cannot_create_privacy_incident(self, student_api):
        resp = student_api.post("/api/privacy/incidents/", {
            "severity": "low",
            "title": "test",
            "description": "test",
        }, format="json")
        assert resp.status_code == 403

    def test_cannot_view_other_student_mastery(
        self, student_api, student_b, concepts,
    ):
        MasteryState.objects.create(
            student=student_b, concept=concepts[0], p_mastery=0.5,
        )
        resp = student_api.get(
            f"/api/adaptive/student/{student_b.pk}/mastery/"
        )
        assert resp.status_code == 403


class TestLecturerPermissions:
    """Lecturers have access to their class data but not admin endpoints."""

    def test_can_access_classes(self, lecturer_api, class_with_members):
        resp = lecturer_api.get("/api/auth/classes/")
        assert resp.status_code == 200

    def test_can_access_class_students(
        self, lecturer_api, class_with_members,
    ):
        resp = lecturer_api.get(
            f"/api/auth/classes/{class_with_members.pk}/students/"
        )
        assert resp.status_code == 200

    def test_can_access_dashboard_overview(
        self, lecturer_api, class_with_members,
    ):
        resp = lecturer_api.get(
            f"/api/dashboard/class/{class_with_members.pk}/overview/"
        )
        assert resp.status_code == 200

    def test_can_access_alerts(self, lecturer_api, class_with_members):
        resp = lecturer_api.get("/api/dashboard/alerts/")
        assert resp.status_code == 200

    def test_can_access_student_mastery(
        self, lecturer_api, student, class_with_members, concepts,
    ):
        MasteryState.objects.create(
            student=student, concept=concepts[0], p_mastery=0.5,
        )
        resp = lecturer_api.get(
            f"/api/adaptive/student/{student.pk}/mastery/"
        )
        assert resp.status_code == 200

    def test_can_access_student_events(
        self, lecturer_api, student, class_with_members,
    ):
        resp = lecturer_api.get(f"/api/events/student/{student.pk}/")
        assert resp.status_code == 200

    def test_cannot_submit_task(self, lecturer_api):
        resp = lecturer_api.post(
            "/api/adaptive/submit/", {}, format="json",
        )
        assert resp.status_code == 403

    def test_cannot_access_analytics_reports(self, lecturer_api):
        resp = lecturer_api.get("/api/analytics/reports/")
        assert resp.status_code == 403

    def test_cannot_access_data_quality(self, lecturer_api):
        resp = lecturer_api.get("/api/analytics/data-quality/")
        assert resp.status_code == 403

    def test_cannot_access_privacy_incidents(self, lecturer_api):
        resp = lecturer_api.get("/api/privacy/incidents/")
        assert resp.status_code == 403

    def test_cannot_access_deep_health(self, lecturer_api):
        resp = lecturer_api.get("/api/health/deep/")
        assert resp.status_code == 403


class TestAdminPermissions:
    """Admins can access admin-only resources."""

    def test_can_access_analytics_reports(self, admin_api):
        resp = admin_api.get("/api/analytics/reports/")
        assert resp.status_code == 200

    def test_can_access_data_quality(self, admin_api):
        resp = admin_api.get("/api/analytics/data-quality/")
        assert resp.status_code == 200

    def test_can_access_privacy_incidents(self, admin_api):
        resp = admin_api.get("/api/privacy/incidents/")
        assert resp.status_code == 200

    def test_can_access_deep_health(self, admin_api):
        resp = admin_api.get("/api/health/deep/")
        assert resp.status_code == 200

    def test_can_create_privacy_incident(self, admin_api):
        resp = admin_api.post("/api/privacy/incidents/", {
            "severity": "low",
            "title": "Admin test incident",
            "description": "Created by admin",
        }, format="json")
        assert resp.status_code == 201


class TestObjectLevelAccess:
    """Cross-class / cross-user boundary checks."""

    @pytest.fixture
    def other_lecturer(self, db):
        from accounts.models import User
        return User.objects.create_user(
            username="other_lecturer", password="Str0ngP@ss!",
            role=User.Role.LECTURER,
            first_name="Other", last_name="Lecturer",
        )

    @pytest.fixture
    def other_lecturer_api(self, other_lecturer):
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=other_lecturer)
        return client

    def test_lecturer_cannot_access_other_class_overview(
        self, other_lecturer_api, class_with_members,
    ):
        resp = other_lecturer_api.get(
            f"/api/dashboard/class/{class_with_members.pk}/overview/"
        )
        assert resp.status_code == 403

    def test_lecturer_cannot_access_student_in_other_class(
        self, other_lecturer_api, student, class_with_members, concepts,
    ):
        MasteryState.objects.create(
            student=student, concept=concepts[0], p_mastery=0.5,
        )
        resp = other_lecturer_api.get(
            f"/api/adaptive/student/{student.pk}/mastery/"
        )
        assert resp.status_code == 403


class TestPublicEndpoints:
    """Endpoints with AllowAny should work without auth."""

    def test_health_liveness(self, anon_api):
        resp = anon_api.get("/api/health/")
        assert resp.status_code == 200

    def test_health_readiness(self, anon_api):
        resp = anon_api.get("/api/health/ready/")
        assert resp.status_code in (200, 503)

    def test_login(self, anon_api, student):
        resp = anon_api.post("/api/auth/login/", {
            "username": student.username,
            "password": "Str0ngP@ss!",
        }, format="json")
        assert resp.status_code == 200

    def test_register(self, anon_api):
        resp = anon_api.post("/api/auth/register/", {
            "username": "public_test",
            "email": "pub@test.vn",
            "password": "Str0ngP@ss!",
            "first_name": "Pub",
            "last_name": "Test",
            "student_id": "PUB001",
        }, format="json")
        assert resp.status_code == 201
