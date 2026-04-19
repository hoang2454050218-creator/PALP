"""View-level permission classes for the Coach.

The privacy middleware path-pattern gate covers the "production" path
(authenticated cookie + JWT). For tests that use ``force_authenticate``
the middleware sees AnonymousUser and is bypassed — so we duplicate
the consent check at the view layer for defence in depth.
"""
from __future__ import annotations

from rest_framework.permissions import BasePermission

from privacy.services import has_consent


class HasCoachLocalConsent(BasePermission):
    """Student must have ``ai_coach_local`` ConsentRecord granted."""

    message = (
        "Bạn cần bật quyền 'Trợ lý AI nội bộ' trong Quyền riêng tư trước "
        "khi chat với coach."
    )

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
        if not getattr(request.user, "is_student", False):
            return False
        return has_consent(request.user, "ai_coach_local")
