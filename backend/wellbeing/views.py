from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from events.emitter import emit_event
from events.models import EventLog
from palp.idempotency import idempotent
from .models import WellbeingNudge
from .serializers import WellbeingNudgeSerializer, CheckWellbeingSerializer, NudgeResponseSerializer

LIMIT_MINUTES = settings.PALP_WELLBEING["CONTINUOUS_STUDY_LIMIT_MINUTES"]


class CheckWellbeingView(APIView):
    @idempotent(required=False)
    def post(self, request):
        serializer = CheckWellbeingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        minutes = serializer.validated_data["continuous_minutes"]

        if minutes >= LIMIT_MINUTES:
            nudge = WellbeingNudge.objects.create(
                student=request.user,
                nudge_type=WellbeingNudge.NudgeType.BREAK_REMINDER,
                continuous_minutes=minutes,
            )
            emit_event(
                EventLog.EventName.WELLBEING_NUDGE,
                actor=request.user,
                request_id=getattr(request, "request_id", None),
                properties={
                    "nudge_id": nudge.id,
                    "nudge_type": nudge.nudge_type,
                    "continuous_minutes": minutes,
                    "sub_event": "shown",
                },
            )
            return Response({
                "should_nudge": True,
                "nudge": WellbeingNudgeSerializer(nudge).data,
                "message": "Bạn đã học liên tục hơn 50 phút. Hãy nghỉ giải lao một chút nhé!",
            })

        return Response({"should_nudge": False})


class NudgeResponseView(APIView):
    @idempotent(required=False)
    def post(self, request, pk):
        nudge = WellbeingNudge.objects.get(id=pk, student=request.user)
        serializer = NudgeResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nudge.response = serializer.validated_data["response"]
        nudge.responded_at = timezone.now()
        nudge.save()

        event_name = (
            EventLog.EventName.WELLBEING_NUDGE_ACCEPTED
            if nudge.response == WellbeingNudge.NudgeResponse.ACCEPTED
            else EventLog.EventName.WELLBEING_NUDGE_DISMISSED
        )
        emit_event(
            event_name,
            actor=request.user,
            request_id=getattr(request, "request_id", None),
            properties={
                "nudge_id": nudge.id,
                "nudge_type": nudge.nudge_type,
                "response": nudge.response,
            },
        )

        return Response(WellbeingNudgeSerializer(nudge).data)


class MyNudgesView(APIView):
    def get(self, request):
        nudges = WellbeingNudge.objects.filter(student=request.user)[:20]
        return Response(WellbeingNudgeSerializer(nudges, many=True).data)
