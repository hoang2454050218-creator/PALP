"""Verify that previously dead-code middlewares are wired into the chain.

Wave 1 task: AuthAuditMiddleware (login/logout/consent audit) and
RequestIDLoggingMiddleware (log correlation) were defined but never
registered, silently disabling auth audit logs and breaking log correlation.
"""
import logging

import pytest
from django.conf import settings

from palp.middleware import _request_id_ctx, RequestIDLogFilter

pytestmark = pytest.mark.integration


class TestMiddlewareRegistered:
    def test_request_id_logging_middleware_in_chain(self):
        assert "palp.middleware.RequestIDLoggingMiddleware" in settings.MIDDLEWARE

    def test_request_id_middleware_runs_before_logging_one(self):
        chain = settings.MIDDLEWARE
        rid_idx = chain.index("palp.middleware.RequestIDMiddleware")
        log_idx = chain.index("palp.middleware.RequestIDLoggingMiddleware")
        assert rid_idx < log_idx, (
            "RequestIDLoggingMiddleware must run after RequestIDMiddleware"
            " so request.request_id is already populated"
        )

    def test_auth_audit_middleware_in_chain(self):
        assert "accounts.middleware.AuthAuditMiddleware" in settings.MIDDLEWARE

    def test_auth_audit_middleware_runs_after_authentication(self):
        chain = settings.MIDDLEWARE
        auth_idx = chain.index("django.contrib.auth.middleware.AuthenticationMiddleware")
        audit_idx = chain.index("accounts.middleware.AuthAuditMiddleware")
        assert auth_idx < audit_idx, (
            "AuthAuditMiddleware needs request.user populated by AuthenticationMiddleware"
        )


class TestRequestIDLogFilter:
    def setup_method(self):
        # Clean any leftover ContextVar value from previous tests.
        try:
            _request_id_ctx.set(None)
        except LookupError:
            pass

    def _make_record(self):
        return logging.LogRecord(
            name="palp", level=logging.INFO, pathname="x", lineno=1,
            msg="test", args=(), exc_info=None,
        )

    def test_falls_back_to_dash_when_no_context(self):
        record = self._make_record()
        RequestIDLogFilter().filter(record)
        assert record.request_id == "-"

    def test_picks_up_context_var(self):
        token = _request_id_ctx.set("abc-123")
        try:
            record = self._make_record()
            RequestIDLogFilter().filter(record)
            assert record.request_id == "abc-123"
        finally:
            _request_id_ctx.reset(token)

    def test_explicit_extra_takes_precedence_over_context(self):
        token = _request_id_ctx.set("from-ctx")
        try:
            record = self._make_record()
            record.request_id = "from-extra"
            RequestIDLogFilter().filter(record)
            assert record.request_id == "from-extra"
        finally:
            _request_id_ctx.reset(token)


@pytest.mark.django_db
class TestAuthAuditWiring:
    """End-to-end: a successful login should create an AuditLog entry now
    that AuthAuditMiddleware is registered.
    """

    def test_login_writes_audit_entry(self, student):
        from privacy.models import AuditLog
        from rest_framework.test import APIClient

        before = AuditLog.objects.count()
        client = APIClient()
        response = client.post(
            "/api/auth/login/",
            {"username": "test_student", "password": "Str0ngP@ss!"},
            format="json",
        )
        assert response.status_code == 200
        after = AuditLog.objects.count()
        assert after > before, "login should produce at least one AuditLog row"
