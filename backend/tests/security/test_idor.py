import pytest
from adaptive.models import MasteryState

pytestmark = [pytest.mark.django_db, pytest.mark.security]


class TestStudentDataIsolation:

    def test_student_mastery_list_only_own(
        self, student_api, student, student_b, concepts,
    ):
        MasteryState.objects.create(student=student, concept=concepts[0], p_mastery=0.7)
        MasteryState.objects.create(student=student_b, concept=concepts[0], p_mastery=0.5)

        resp = student_api.get("/api/adaptive/mastery/")
        assert resp.status_code == 200
        results = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
        student_ids = {item.get("student", student.pk) for item in results}
        assert student_b.pk not in student_ids

    def test_student_cannot_view_other_student_events(
        self, student_api, student_b,
    ):
        resp = student_api.get(f"/api/events/student/{student_b.pk}/")
        assert resp.status_code == 403

    def test_student_events_list_only_own(self, student_api, student, student_b):
        from events.models import EventLog
        EventLog.objects.create(actor=student, event_name="page_view")
        EventLog.objects.create(actor=student_b, event_name="page_view")

        resp = student_api.get("/api/events/my/")
        assert resp.status_code == 200
        results = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
        for item in results:
            assert item.get("actor") != student_b.pk

    def test_student_cannot_access_dashboard_alerts(self, student_api):
        resp = student_api.get("/api/dashboard/alerts/")
        assert resp.status_code == 403
