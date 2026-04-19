import pytest

pytestmark = pytest.mark.django_db


class TestLinkSessionView:
    def test_creates_canonical(self, student_api):
        resp = student_api.post(
            "/api/sessions/link/",
            data={
                "raw_session_id": "rs-1",
                "raw_fingerprint": "canvas:abcd|audio:efgh|ua:chrome",
                "user_agent_family": "chrome-windows",
                "consent_given": True,
            },
            format="json",
        )
        assert resp.status_code == 201
        assert "canonical_session_id" in resp.data
        assert resp.data["fingerprint_registered"] is True
        assert resp.data["fingerprint_consent"] is True

    def test_idempotent_same_raw_id(self, student_api):
        a = student_api.post(
            "/api/sessions/link/",
            data={"raw_session_id": "rs-1"},
            format="json",
        )
        b = student_api.post(
            "/api/sessions/link/",
            data={"raw_session_id": "rs-1"},
            format="json",
        )
        assert a.status_code == 201
        assert b.status_code == 201
        assert a.data["canonical_session_id"] == b.data["canonical_session_id"]

    def test_anon_rejected(self, anon_api):
        resp = anon_api.post(
            "/api/sessions/link/",
            data={"raw_session_id": "rs-x"},
            format="json",
        )
        assert resp.status_code in (401, 403)

    def test_canonical_lookup_returns_for_owner(self, student_api):
        student_api.post(
            "/api/sessions/link/",
            data={"raw_session_id": "rs-7"},
            format="json",
        )
        resp = student_api.get("/api/sessions/canonical/?raw_session_id=rs-7")
        assert resp.status_code == 200
        assert resp.data["raw_session_id"] == "rs-7"

    def test_canonical_lookup_404_for_other_user(self, student_api, student_b):
        student_api.post(
            "/api/sessions/link/",
            data={"raw_session_id": "rs-belong-A"},
            format="json",
        )
        from rest_framework.test import APIClient

        client_b = APIClient()
        client_b.force_authenticate(user=student_b)
        resp = client_b.get("/api/sessions/canonical/?raw_session_id=rs-belong-A")
        assert resp.status_code == 404
