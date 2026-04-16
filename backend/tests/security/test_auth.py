import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.security]

PROTECTED_ENDPOINTS = [
    ("GET", "/api/auth/profile/"),
    ("GET", "/api/adaptive/mastery/"),
    ("POST", "/api/adaptive/submit/"),
    ("GET", "/api/adaptive/attempts/"),
    ("GET", "/api/adaptive/interventions/"),
    ("GET", "/api/assessment/"),
    ("GET", "/api/assessment/my-sessions/"),
    ("GET", "/api/events/my/"),
    ("POST", "/api/events/track/"),
    ("POST", "/api/wellbeing/check/"),
    ("GET", "/api/wellbeing/my/"),
    ("GET", "/api/dashboard/alerts/"),
    ("GET", "/api/dashboard/interventions/history/"),
]


class TestUnauthenticatedAccess:

    @pytest.mark.parametrize("method,url", PROTECTED_ENDPOINTS)
    def test_unauthenticated_returns_401(self, anon_api, method, url):
        dispatch = getattr(anon_api, method.lower())
        response = dispatch(url)
        assert response.status_code == 401


class TestTokenSecurity:

    def test_invalid_token_rejected(self, anon_api):
        anon_api.credentials(HTTP_AUTHORIZATION="Bearer invalid-garbage-token")
        response = anon_api.get("/api/auth/profile/")
        assert response.status_code == 401

    def test_malformed_auth_header_rejected(self, anon_api):
        anon_api.credentials(HTTP_AUTHORIZATION="NotBearer some-token")
        response = anon_api.get("/api/auth/profile/")
        assert response.status_code == 401

    def test_refresh_token_returns_new_access(self, student, anon_api):
        login_resp = anon_api.post("/api/auth/login/", {
            "username": student.username,
            "password": "Str0ngP@ss!",
        }, format="json")
        assert login_resp.status_code == 200
        refresh_token = login_resp.data["refresh"]

        refresh_resp = anon_api.post("/api/auth/token/refresh/", {
            "refresh": refresh_token,
        }, format="json")
        assert refresh_resp.status_code == 200
        assert "access" in refresh_resp.data
