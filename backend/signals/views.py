"""
Signals API.

Endpoints:
  POST /api/signals/ingest/   -> batch ingest, idempotent per event
  GET  /api/signals/my/        -> last 50 SignalSession rows for the caller
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SignalSession
from .permissions import IsStudentWithSignalsConsent
from .serializers import SignalIngestSerializer, SignalSessionSerializer
from .services import ingest_events


class SignalIngestView(APIView):
    permission_classes = (IsAuthenticated, IsStudentWithSignalsConsent)

    def post(self, request):
        serializer = SignalIngestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result = ingest_events(
            student=request.user,
            raw_session_id=data["raw_session_id"],
            canonical_session_id=data.get("canonical_session_id"),
            events=data["events"],
        )
        return Response(result, status=status.HTTP_202_ACCEPTED)


class MySignalsView(APIView):
    permission_classes = (IsAuthenticated, IsStudentWithSignalsConsent)

    def get(self, request):
        rows = (
            SignalSession.objects
            .filter(student=request.user)
            .order_by("-window_start")[:50]
        )
        payload = []
        for r in rows:
            payload.append({
                "canonical_session_id": r.canonical_session_id,
                "raw_session_id": r.raw_session_id,
                "window_start": r.window_start,
                "window_end": r.window_end,
                "focus_minutes": r.focus_minutes,
                "idle_minutes": r.idle_minutes,
                "tab_switches": r.tab_switches,
                "hint_count": r.hint_count,
                "frustration_score": r.frustration_score,
                "give_up_count": r.give_up_count,
                "response_time_outliers": r.response_time_outliers,
                "struggle_count": r.struggle_count,
                "raw_event_count": r.raw_event_count,
                "session_quality": r.session_quality,
            })
        return Response({"sessions": payload, "count": len(payload)})
