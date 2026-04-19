from __future__ import annotations

from rest_framework.permissions import BasePermission, SAFE_METHODS


def _is_admin(user) -> bool:
    return bool(
        getattr(user, "is_staff", False)
        or getattr(user, "is_superuser", False)
        or getattr(user, "is_admin_user", False)
    )


class IsAdminOrPI(BasePermission):
    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return _is_admin(user) or getattr(user, "is_lecturer", False)
        return _is_admin(user)


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "is_student", False)
        )
