"""Peer endpoint permissions.

Two custom checks layered on top of ``IsStudent``/``IsLecturer``:

* ``HasPeerComparisonConsent`` and ``HasPeerTeachingConsent`` are
  redundant with the middleware-level consent gate but kept here so
  the view layer can fail fast without an extra middleware roundtrip
  during background pre-render checks.
* ``IsLecturerOfClass`` makes sure herd-cluster endpoints only return
  data for classes the lecturer is assigned to.
"""
from __future__ import annotations

from rest_framework.permissions import BasePermission

from accounts.permissions import IsLecturer, IsStudent  # noqa: F401 (re-export)
from privacy.services import has_consent


class HasPeerComparisonConsent(BasePermission):
    """Student must have ``peer_comparison`` consent."""

    message = (
        "Bạn cần đồng ý 'so sánh ẩn danh trong cohort' để dùng tính năng này."
    )

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
        if not getattr(request.user, "is_student", False):
            return False
        return has_consent(request.user, "peer_comparison")


class HasPeerTeachingConsent(BasePermission):
    """Student must have ``peer_teaching`` consent."""

    message = (
        "Bạn cần đồng ý 'ghép cặp dạy nhau' để dùng tính năng này."
    )

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
        if not getattr(request.user, "is_student", False):
            return False
        return has_consent(request.user, "peer_teaching")


class IsLecturerOfClass(BasePermission):
    """Lecturer must be assigned to the class referenced in the URL."""

    message = "Bạn không phụ trách lớp này."

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
        if not getattr(request.user, "is_lecturer", False) and not getattr(
            request.user, "is_admin_user", False
        ):
            return False

        class_id = view.kwargs.get("class_id") or request.query_params.get("class_id")
        if not class_id:
            return True  # let the view enforce class membership per-row

        if getattr(request.user, "is_admin_user", False):
            return True

        from accounts.models import LecturerClassAssignment
        return LecturerClassAssignment.objects.filter(
            lecturer=request.user, student_class_id=class_id,
        ).exists()
