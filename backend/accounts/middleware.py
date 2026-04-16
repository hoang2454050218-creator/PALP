"""
Supplementary audit middleware for auth-specific actions (login, logout, consent).
The primary audit middleware lives in privacy.middleware.AuditMiddleware.
"""
from django.utils.deprecation import MiddlewareMixin

from .audit import log_audit


class AuthAuditMiddleware(MiddlewareMixin):
    """Logs auth-specific events not covered by the privacy audit middleware."""

    AUTH_PATHS = {
        "/api/auth/login/": "login",
        "/api/auth/logout/": "logout",
        "/api/auth/consent/": "consent_change",
    }

    def process_response(self, request, response):
        if request.method != "POST":
            return response

        path = request.path
        action = self.AUTH_PATHS.get(path)
        if not action:
            return response

        if action == "login":
            if response.status_code == 200:
                log_audit(action="login", request=request, status_code=200)
            elif response.status_code in (400, 401):
                log_audit(action="login_failed", request=request, status_code=response.status_code)
        elif action == "logout" and response.status_code == 200:
            log_audit(action="logout", request=request, status_code=200)
        elif action == "consent_change" and response.status_code == 200:
            log_audit(action="consent_change", request=request, status_code=200)

        return response
