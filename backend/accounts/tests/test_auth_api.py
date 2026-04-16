import pytest
from rest_framework import status

pytestmark = pytest.mark.django_db

LOGIN_URL = "/api/auth/login/"
PROFILE_URL = "/api/auth/profile/"
CONSENT_URL = "/api/auth/consent/"
CLASSES_URL = "/api/auth/classes/"
TOKEN_REFRESH_URL = "/api/auth/token/refresh/"


class TestLogin:
    def test_valid_credentials_returns_tokens(self, anon_api, student):
        resp = anon_api.post(LOGIN_URL, {"username": "test_student", "password": "Str0ngP@ss!"})
        assert resp.status_code == status.HTTP_200_OK
        assert "access" in resp.data
        assert "refresh" in resp.data

    def test_wrong_password_returns_401(self, anon_api, student):
        resp = anon_api.post(LOGIN_URL, {"username": "test_student", "password": "WrongPass"})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestProfile:
    def test_authenticated_returns_profile(self, student_api, student):
        resp = student_api.get(PROFILE_URL)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["username"] == student.username
        assert resp.data["role"] == "student"

    def test_unauthenticated_returns_401(self, anon_api):
        resp = anon_api.get(PROFILE_URL)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestConsent:
    def test_consent_sets_flag_and_timestamp(self, student_api, student):
        resp = student_api.post(CONSENT_URL, {"consent_given": True})
        assert resp.status_code == status.HTTP_200_OK
        student.refresh_from_db()
        assert student.consent_given is True
        assert student.consent_given_at is not None


class TestClassesList:
    def test_student_forbidden(self, student_api):
        resp = student_api.get(CLASSES_URL)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_lecturer_allowed(self, lecturer_api):
        resp = lecturer_api.get(CLASSES_URL)
        assert resp.status_code == status.HTTP_200_OK


class TestTokenRefresh:
    def test_valid_refresh_returns_new_access(self, anon_api, student):
        login_resp = anon_api.post(LOGIN_URL, {"username": "test_student", "password": "Str0ngP@ss!"})
        refresh = login_resp.data["refresh"]
        resp = anon_api.post(TOKEN_REFRESH_URL, {"refresh": refresh})
        assert resp.status_code == status.HTTP_200_OK
        assert "access" in resp.data
