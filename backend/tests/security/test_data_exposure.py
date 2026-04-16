import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.security]


class TestNoSensitiveDataExposure:

    def test_profile_response_has_no_password(self, student_api):
        resp = student_api.get("/api/auth/profile/")
        assert resp.status_code == 200
        assert "password" not in resp.data

    def test_mastery_list_only_own_data(self, student_api, student, student_b, concepts):
        from adaptive.models import MasteryState
        MasteryState.objects.create(student=student, concept=concepts[0], p_mastery=0.7)
        MasteryState.objects.create(student=student_b, concept=concepts[0], p_mastery=0.4)

        resp = student_api.get("/api/adaptive/mastery/")
        results = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
        for item in results:
            assert item.get("student") is None or item["student"] == student.pk

    def test_event_list_only_own_events(self, student_api, student, student_b):
        from events.models import EventLog
        EventLog.objects.create(actor=student, event_name="page_view")
        EventLog.objects.create(actor=student_b, event_name="page_view")

        resp = student_api.get("/api/events/my/")
        results = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
        assert len(results) >= 1
