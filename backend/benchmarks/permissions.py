from __future__ import annotations

from rest_framework.permissions import BasePermission


def _is_admin(user) -> bool:
    return bool(
        getattr(user, "is_staff", False)
        or getattr(user, "is_superuser", False)
        or getattr(user, "is_admin_user", False)
    )


class IsAdminOrLecturer(BasePermission):
    """Benchmarks are an internal infrastructure surface.

    Students never see them; lecturers may inspect for transparency,
    but only admins may trigger a run.
    """

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return _is_admin(user) or getattr(user, "is_lecturer", False)
        return _is_admin(user)
