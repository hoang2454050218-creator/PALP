"""
DRF permission gates for the signals app.

The ingest endpoint requires:
* the user to be authenticated (handled by global default).
* the user to be a student (lecturers/admins don't generate sensing data).
* the user to have granted the ``behavioral_signals`` consent purpose.

The middleware-level gate already blocks the path prefix; this view-
level check provides a clean DRF permission denied (403) that the
serializer/test layer can rely on.
"""
from rest_framework.permissions import BasePermission

from accounts.models import User
from privacy.services import has_consent


class IsStudentWithSignalsConsent(BasePermission):
    message = "Bạn cần đồng ý 'behavioral_signals' để gửi tín hiệu hành vi."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        role = getattr(user, "role", None)
        if role != User.Role.STUDENT:
            return False
        return has_consent(user, "behavioral_signals")
