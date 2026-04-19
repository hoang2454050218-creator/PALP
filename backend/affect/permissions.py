from __future__ import annotations

from rest_framework.permissions import BasePermission

from privacy.services import has_consent


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "is_student", False)
        )


class HasAffectConsent(BasePermission):
    """Defence-in-depth — `force_authenticate` skips the middleware."""

    message = (
        "Bạn cần đồng ý 'affect_signals' trong Quyền riêng tư trước khi "
        "sử dụng tính năng phân tích cảm xúc."
    )

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        return has_consent(user, "affect_signals")
