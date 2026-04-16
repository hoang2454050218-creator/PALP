import pytest
from rest_framework import status

pytestmark = pytest.mark.django_db


class TestTrackEvent:

    def test_creates_event_returns_201(self, student_api):
        resp = student_api.post("/api/events/track/", {
            "event_name": "session_started",
        }, format="json")
        assert resp.status_code == status.HTTP_201_CREATED

    def test_unauthenticated_gets_401(self, anon_api):
        resp = anon_api.post("/api/events/track/", {
            "event_name": "session_started",
        }, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestBatchTrack:

    def test_creates_multiple_events(self, student_api):
        resp = student_api.post("/api/events/batch/", {
            "events": [
                {"event_name": "page_view"},
                {"event_name": "page_view"},
            ],
        }, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["tracked"] == 2

    def test_unauthenticated_gets_401(self, anon_api):
        resp = anon_api.post("/api/events/batch/", {
            "events": [{"event_name": "page_view"}],
        }, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestMyEvents:

    def test_returns_own_events(self, student_api):
        student_api.post("/api/events/track/", {
            "event_name": "page_view",
        }, format="json")
        resp = student_api.get("/api/events/my/")
        assert resp.status_code == status.HTTP_200_OK

    def test_unauthenticated_gets_401(self, anon_api):
        resp = anon_api.get("/api/events/my/")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestStudentEvents:

    def test_lecturer_can_view(self, lecturer_api, student, class_with_members):
        resp = lecturer_api.get(f"/api/events/student/{student.pk}/")
        assert resp.status_code == status.HTTP_200_OK

    def test_student_gets_403(self, student_api, student_b):
        resp = student_api.get(f"/api/events/student/{student_b.pk}/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_gets_401(self, anon_api, student):
        resp = anon_api.get(f"/api/events/student/{student.pk}/")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
