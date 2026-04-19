"""HTTP endpoints for the Emergency Pipeline.

| Method | Path                              | Auth                       |
| ------ | --------------------------------- | -------------------------- |
| GET    | ``contact/``                       | IsStudent (own)            |
| PATCH  | ``contact/``                       | IsStudent (own)            |
| GET    | ``queue/``                         | IsLecturer (counselor)     |
| GET    | ``events/<id>/``                   | IsLecturer of student      |
| POST   | ``events/<id>/acknowledge/``       | IsLecturer of student      |
| POST   | ``events/<id>/resolve/``           | IsLecturer of student      |
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsLecturer, IsLecturerOrAdmin, IsStudent

from emergency.models import (
    CounselorQueueEntry,
    EmergencyContact,
    EmergencyEvent,
)
from emergency.serializers import (
    CounselorQueueEntrySerializer,
    EmergencyContactSerializer,
    EmergencyEventSerializer,
)
from emergency.services import acknowledge as svc_ack, resolve as svc_resolve


class EmergencyContactView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        contact = EmergencyContact.objects.filter(student=request.user).first()
        if not contact:
            return Response(
                {"contact": None, "message": "Bạn chưa thêm liên hệ khẩn cấp."},
            )
        return Response(EmergencyContactSerializer(contact).data)

    def patch(self, request):
        from django.utils import timezone

        contact, _ = EmergencyContact.objects.get_or_create(
            student=request.user,
            defaults={"name": "(chưa đặt)", "relationship": "other"},
        )
        serializer = EmergencyContactSerializer(
            contact, data=request.data, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        previous_consent = contact.consent_given
        contact = serializer.save()

        if request.data.get("consent_given") is True and not previous_consent:
            contact.consent_given = True
            contact.consent_given_at = timezone.now()
            contact.save(update_fields=["consent_given", "consent_given_at"])
        elif request.data.get("consent_given") is False:
            contact.consent_given = False
            contact.save(update_fields=["consent_given"])

        return Response(EmergencyContactSerializer(contact).data)


class CounselorQueueView(APIView):
    permission_classes = [IsAuthenticated, IsLecturerOrAdmin]

    def get(self, request):
        qs = (
            CounselorQueueEntry.objects
            .filter(counselor=request.user)
            .exclude(state__in=[
                CounselorQueueEntry.State.EXPIRED,
                CounselorQueueEntry.State.DECLINED,
            ])
            .select_related("event", "event__student")
            .order_by("-queued_at")[:50]
        )
        return Response(
            {"entries": CounselorQueueEntrySerializer(qs, many=True).data}
        )


class EmergencyEventDetailView(APIView):
    permission_classes = [IsAuthenticated, IsLecturer]

    def get(self, request, event_id):
        event = (
            EmergencyEvent.objects
            .filter(id=event_id)
            .select_related("student")
            .first()
        )
        if not event:
            return Response(
                {"detail": "Không tìm thấy sự kiện."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not _is_authorised_counselor(request.user, event):
            return Response(
                {"detail": "Bạn không phụ trách sinh viên này."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(EmergencyEventSerializer(event).data)


class EmergencyAcknowledgeView(APIView):
    permission_classes = [IsAuthenticated, IsLecturer]

    def post(self, request, event_id):
        event = EmergencyEvent.objects.filter(id=event_id).first()
        if not event:
            return Response(
                {"detail": "Không tìm thấy sự kiện."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not _is_authorised_counselor(request.user, event):
            return Response(
                {"detail": "Bạn không phụ trách sinh viên này."},
                status=status.HTTP_403_FORBIDDEN,
            )
        event = svc_ack(
            event=event,
            counselor=request.user,
            notes=request.data.get("notes", ""),
        )
        return Response(EmergencyEventSerializer(event).data)


class EmergencyResolveView(APIView):
    permission_classes = [IsAuthenticated, IsLecturer]

    def post(self, request, event_id):
        event = EmergencyEvent.objects.filter(id=event_id).first()
        if not event:
            return Response(
                {"detail": "Không tìm thấy sự kiện."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not _is_authorised_counselor(request.user, event):
            return Response(
                {"detail": "Bạn không phụ trách sinh viên này."},
                status=status.HTTP_403_FORBIDDEN,
            )
        event = svc_resolve(
            event=event,
            counselor=request.user,
            notes=request.data.get("notes", ""),
        )
        return Response(EmergencyEventSerializer(event).data)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_authorised_counselor(user, event) -> bool:
    if getattr(user, "is_admin_user", False):
        return True
    from accounts.models import LecturerClassAssignment, ClassMembership

    student_class_ids = ClassMembership.objects.filter(
        student=event.student
    ).values_list("student_class_id", flat=True)
    return LecturerClassAssignment.objects.filter(
        lecturer=user, student_class_id__in=student_class_ids,
    ).exists()
