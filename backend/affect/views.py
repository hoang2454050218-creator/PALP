from __future__ import annotations

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AffectSnapshot
from .permissions import HasAffectConsent, IsStudent
from .serializers import AffectSnapshotSerializer
from .services import fuse, ingest_keystroke, ingest_linguistic, recent_for


class IngestKeystrokeView(APIView):
    permission_classes = [IsAuthenticated, IsStudent, HasAffectConsent]

    def post(self, request):
        payload = request.data.get("metrics") or {}
        if not isinstance(payload, dict):
            return Response(
                {"detail": "metrics must be an object."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        snap = ingest_keystroke(
            request.user,
            payload,
            duration_ms=int(request.data.get("duration_ms", 0)),
        )
        return Response(
            AffectSnapshotSerializer(snap).data,
            status=status.HTTP_201_CREATED,
        )


class IngestLinguisticView(APIView):
    permission_classes = [IsAuthenticated, IsStudent, HasAffectConsent]

    def post(self, request):
        text = request.data.get("text") or ""
        snap = ingest_linguistic(
            request.user,
            text,
            language=request.data.get("language"),
            duration_ms=int(request.data.get("duration_ms", 0)),
        )
        return Response(
            AffectSnapshotSerializer(snap).data,
            status=status.HTTP_201_CREATED,
        )


class IngestFusedView(APIView):
    permission_classes = [IsAuthenticated, IsStudent, HasAffectConsent]

    def post(self, request):
        snap = fuse(
            request.user,
            keystroke_payload=request.data.get("metrics") or None,
            text=request.data.get("text") or None,
            language=request.data.get("language"),
            duration_ms=int(request.data.get("duration_ms", 0)),
        )
        return Response(
            AffectSnapshotSerializer(snap).data,
            status=status.HTTP_201_CREATED,
        )


class MyRecentAffectView(generics.ListAPIView):
    serializer_class = AffectSnapshotSerializer
    permission_classes = [IsAuthenticated, IsStudent, HasAffectConsent]

    def get_queryset(self):
        limit = int(self.request.query_params.get("limit", 20))
        return list(recent_for(self.request.user, limit=max(1, min(limit, 100))))
