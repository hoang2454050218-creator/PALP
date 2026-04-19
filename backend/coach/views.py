"""HTTP endpoints for the AI Coach.

| Method | Path                                   | Auth                           |
| ------ | -------------------------------------- | ------------------------------ |
| GET    | ``consent/``                            | IsStudent                      |
| PATCH  | ``consent/``                            | IsStudent                      |
| POST   | ``message/``                            | IsStudent + ai_coach_local     |
| GET    | ``conversations/``                      | IsStudent (own only)           |
| GET    | ``conversations/<id>/``                 | IsStudent (own only)           |
| POST   | ``conversations/<id>/end/``             | IsStudent (own only)           |

Note: the ``message`` endpoint is the one consent-gated by the privacy
middleware. The list / detail / end endpoints are intentionally always
reachable so the student can browse history + stop the chat without
needing to grant new consent.
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsStudent

from coach.models import CoachConsent, CoachConversation
from coach.permissions import HasCoachLocalConsent
from coach.serializers import (
    CoachConsentSerializer,
    CoachConversationListSerializer,
    CoachConversationSerializer,
    CoachTurnSerializer,
)
from coach.services import process_message


def _ensure_consent(user) -> CoachConsent:
    consent, _ = CoachConsent.objects.get_or_create(student=user)
    return consent


class CoachConsentView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        consent = _ensure_consent(request.user)
        return Response(CoachConsentSerializer(consent).data)

    def patch(self, request):
        consent = _ensure_consent(request.user)
        serializer = CoachConsentSerializer(
            consent, data=request.data, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        previous = {
            "ai_coach_local": consent.ai_coach_local,
            "ai_coach_cloud": consent.ai_coach_cloud,
            "share_emergency_contact": consent.share_emergency_contact,
        }
        consent = serializer.save()

        from privacy.constants import CONSENT_VERSION
        from privacy.models import ConsentRecord

        for purpose in (
            "ai_coach_local", "ai_coach_cloud", "emergency_contact",
        ):
            field = "share_emergency_contact" if purpose == "emergency_contact" else purpose
            new_val = getattr(consent, field)
            if new_val != previous[field]:
                ConsentRecord.objects.create(
                    user=request.user,
                    purpose=purpose,
                    granted=new_val,
                    version=CONSENT_VERSION,
                )

        return Response(CoachConsentSerializer(consent).data)


class CoachMessageView(APIView):
    permission_classes = [IsAuthenticated, IsStudent, HasCoachLocalConsent]

    def post(self, request):
        text = (request.data.get("text") or "").strip()
        if not text:
            return Response(
                {"detail": "text is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = process_message(student=request.user, text=text)

        return Response(
            {
                "conversation_id": result.conversation.id,
                "student_turn": CoachTurnSerializer(result.student_turn).data,
                "assistant_turn": CoachTurnSerializer(result.assistant_turn).data,
                "emergency_triggered": result.emergency_triggered,
                "emergency_event_id": result.emergency_event_id,
                "refusal_kind": result.refusal_kind,
            },
            status=status.HTTP_201_CREATED,
        )


class CoachConversationListView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        qs = (
            CoachConversation.objects
            .filter(student=request.user)
            .order_by("-started_at")[:20]
        )
        return Response(
            {"conversations": CoachConversationListSerializer(qs, many=True).data}
        )


class CoachConversationDetailView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request, conversation_id):
        conv = (
            CoachConversation.objects
            .filter(student=request.user, id=conversation_id)
            .prefetch_related("turns")
            .first()
        )
        if not conv:
            return Response(
                {"detail": "Không tìm thấy cuộc trò chuyện."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(CoachConversationSerializer(conv).data)


class CoachConversationEndView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def post(self, request, conversation_id):
        from django.utils import timezone

        conv = (
            CoachConversation.objects
            .filter(student=request.user, id=conversation_id)
            .first()
        )
        if not conv:
            return Response(
                {"detail": "Không tìm thấy cuộc trò chuyện."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if conv.status != CoachConversation.Status.OPEN:
            return Response(CoachConversationSerializer(conv).data)
        conv.status = CoachConversation.Status.ENDED
        conv.ended_at = timezone.now()
        conv.save(update_fields=["status", "ended_at"])
        return Response(CoachConversationSerializer(conv).data)
