"""View-level consent gate (defence-in-depth vs the privacy middleware)."""
from __future__ import annotations

from rest_framework.permissions import BasePermission

from privacy.services import has_consent


class HasAgenticMemoryConsent(BasePermission):
    """Student must have ``agentic_memory`` ConsentRecord granted."""

    message = (
        "Bạn cần bật quyền 'Trí nhớ cá nhân hoá của coach' trong Quyền "
        "riêng tư trước khi xem dữ liệu này."
    )

    def has_permission(self, request, view) -> bool:
        # ``DELETE`` is intentionally always allowed (right to be forgotten).
        if request.method == "DELETE":
            return True
        if not (request.user and request.user.is_authenticated):
            return False
        if not getattr(request.user, "is_student", False):
            return False
        return has_consent(request.user, "agentic_memory")
