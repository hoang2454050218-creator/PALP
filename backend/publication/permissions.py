from __future__ import annotations

from rest_framework.permissions import BasePermission, SAFE_METHODS


def _is_admin(user) -> bool:
    return bool(
        getattr(user, "is_staff", False)
        or getattr(user, "is_superuser", False)
        or getattr(user, "is_admin_user", False)
    )


class IsAdminOrLecturer(BasePermission):
    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return _is_admin(user) or getattr(user, "is_lecturer", False)
        return _is_admin(user)


class IsPublicOrAdmin(BasePermission):
    """Read access for any authenticated user when status=published."""

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        return request.method in SAFE_METHODS or _is_admin(user)
