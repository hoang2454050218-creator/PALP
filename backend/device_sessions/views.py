"""
Endpoints for device session linking.

Mounted under ``/api/sessions/`` (NOT ``django.contrib.sessions``).
"""
import logging

from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .linker import link_session, register_device

logger = logging.getLogger("palp")


class _LinkRequestSerializer(serializers.Serializer):
    raw_session_id = serializers.CharField(max_length=120)
    raw_fingerprint = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    user_agent_family = serializers.CharField(
        max_length=80, required=False, allow_blank=True, default=""
    )
    consent_given = serializers.BooleanField(default=False)


class LinkSessionView(APIView):
    """POST: stitch a raw session id to a canonical session for the caller."""

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = _LinkRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        fingerprint = None
        if data.get("raw_fingerprint"):
            fingerprint = register_device(
                user=request.user,
                raw_fingerprint=data["raw_fingerprint"],
                user_agent_family=data.get("user_agent_family", ""),
                consent_given=data["consent_given"],
            )

        canonical = link_session(
            user=request.user,
            raw_session_id=data["raw_session_id"],
            fingerprint=fingerprint,
        )

        return Response(
            {
                "canonical_session_id": str(canonical.canonical_id),
                "is_new_canonical_session": canonical.last_event_at == canonical.started_at,
                "fingerprint_registered": fingerprint is not None,
                "fingerprint_consent": getattr(fingerprint, "consent_given", False),
            },
            status=status.HTTP_201_CREATED,
        )


class CanonicalLookupView(APIView):
    """GET: read-only lookup of the canonical session for a raw id."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        raw = request.query_params.get("raw_session_id")
        if not raw:
            return Response(
                {"detail": "raw_session_id query param required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from .models import SessionLink

        link = SessionLink.objects.filter(
            raw_session_id=raw,
            canonical_session__user=request.user,
        ).select_related("canonical_session").first()
        if not link:
            return Response({"detail": "No canonical session for that raw id."}, status=404)
        return Response({
            "raw_session_id": raw,
            "canonical_session_id": str(link.canonical_session.canonical_id),
            "started_at": link.canonical_session.started_at,
            "last_event_at": link.canonical_session.last_event_at,
        })
