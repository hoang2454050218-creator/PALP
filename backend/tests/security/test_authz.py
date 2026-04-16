import pytest
from dashboard.models import Alert

pytestmark = [pytest.mark.django_db, pytest.mark.security]


class TestStudentRestrictions:

    def test_student_cannot_access_dashboard_overview(
        self, student_api, class_with_members,
    ):
        resp = student_api.get(f"/api/dashboard/class/{class_with_members.pk}/overview/")
        assert resp.status_code == 403

    def test_student_cannot_access_alerts(self, student_api):
        resp = student_api.get("/api/dashboard/alerts/")
        assert resp.status_code == 403

    def test_student_cannot_access_other_student_events(
        self, student_api, student_b,
    ):
        resp = student_api.get(f"/api/events/student/{student_b.pk}/")
        assert resp.status_code == 403

    def test_student_cannot_access_analytics_kpi(self, student_api):
        resp = student_api.get("/api/analytics/kpi/1/")
        assert resp.status_code == 403

    def test_student_cannot_dismiss_alert(
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

    def test_student_cannot_create_intervention(self, student_api):
        resp = student_api.post("/api/dashboard/interventions/", {}, format="json")
        assert resp.status_code == 403


class TestLecturerPermissions:

    def test_lecturer_can_access_dashboard(self, lecturer_api, class_with_members):
        resp = lecturer_api.get(f"/api/dashboard/class/{class_with_members.pk}/overview/")
        assert resp.status_code == 200

    def test_lecturer_can_access_student_mastery(
        self, lecturer_api, student, class_with_members, concepts,
    ):
        from adaptive.models import MasteryState
        MasteryState.objects.create(student=student, concept=concepts[0], p_mastery=0.5)
        resp = lecturer_api.get(f"/api/adaptive/student/{student.pk}/mastery/")
        assert resp.status_code == 200

    def test_lecturer_cannot_submit_task(self, lecturer_api):
        resp = lecturer_api.post("/api/adaptive/submit/", {}, format="json")
        assert resp.status_code == 403
