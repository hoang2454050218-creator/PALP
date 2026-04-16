from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from accounts.permissions import IsLecturerOrAdmin, IsStudentInLecturerClass
from privacy.constants import LECTURER_VISIBLE_EVENTS
from .emitter import emit_event
from .models import EventLog
from .serializers import EventLogSerializer, TrackEventSerializer, BatchTrackSerializer


class TrackEventView(APIView):
    serializer_class = TrackEventSerializer

    def post(self, request):
        serializer = TrackEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        event = emit_event(
            d["event_name"],
            actor=request.user,
            session_id=d.get("session_id", ""),
            device_type=d.get("device_type", ""),
            source_page=d.get("source_page", ""),
            client_timestamp=d.get("client_timestamp"),
            idempotency_key=d.get("idempotency_key") or None,
            request_id=getattr(request, "request_id", None),
            course=d.get("course_id"),
            student_class=d.get("class_id"),
            concept=d.get("concept_id"),
            task=d.get("task_id"),
            difficulty_level=d.get("difficulty_level"),
            attempt_number=d.get("attempt_number"),
            mastery_before=d.get("mastery_before"),
            mastery_after=d.get("mastery_after"),
            intervention_reason=d.get("intervention_reason", ""),
            properties=d.get("properties", {}),
        )

        if event is None:
            return Response(
                {"detail": "Failed to track event."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            EventLogSerializer(event).data,
            status=status.HTTP_201_CREATED,
        )


class BatchTrackView(APIView):
    serializer_class = BatchTrackSerializer

    @transaction.atomic
    def post(self, request):
        serializer = BatchTrackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        created = []
        errors = []
        for idx, ev in enumerate(serializer.validated_data["events"]):
            event = emit_event(
                ev["event_name"],
                actor=request.user,
                session_id=ev.get("session_id", ""),
                device_type=ev.get("device_type", ""),
                source_page=ev.get("source_page", ""),
                client_timestamp=ev.get("client_timestamp"),
                idempotency_key=ev.get("idempotency_key") or None,
                request_id=getattr(request, "request_id", None),
                course=ev.get("course_id"),
                student_class=ev.get("class_id"),
                concept=ev.get("concept_id"),
                task=ev.get("task_id"),
                difficulty_level=ev.get("difficulty_level"),
                attempt_number=ev.get("attempt_number"),
                mastery_before=ev.get("mastery_before"),
                mastery_after=ev.get("mastery_after"),
                intervention_reason=ev.get("intervention_reason", ""),
                properties=ev.get("properties", {}),
            )
            if event:
                created.append(event.id)
            else:
                errors.append(idx)

        return Response(
            {"tracked": len(created), "errors": errors},
            status=status.HTTP_201_CREATED,
        )


class MyEventsView(generics.ListAPIView):
    serializer_class = EventLogSerializer

    def get_queryset(self):
        qs = EventLog.objects.filter(actor=self.request.user)
        event_name = self.request.query_params.get("event_name")
        if event_name:
            qs = qs.filter(event_name=event_name)
        return qs[:100]


class StudentEventsView(generics.ListAPIView):
    serializer_class = EventLogSerializer
    permission_classes = (IsLecturerOrAdmin, IsStudentInLecturerClass)

    def get_queryset(self):
        qs = EventLog.objects.filter(actor_id=self.kwargs["student_id"])

        if self.request.user.is_lecturer:
            qs = qs.filter(event_name__in=LECTURER_VISIBLE_EVENTS)

        return qs[:100]
