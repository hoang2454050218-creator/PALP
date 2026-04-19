"""
HTTP layer for metacognitive calibration (Phase 1E).

Two endpoints:

* ``POST /api/adaptive/calibration/`` — record a pre-submission confidence
  rating. Returns the new ``MetacognitiveJudgment`` id so the client can
  send it back with the submit call (tying confidence to the answer).
* ``GET  /api/adaptive/calibration/me/`` — recent judgments + diagnostic
  pattern for the calling student.
"""
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsStudent
from curriculum.models import MicroTask
from privacy.services import has_consent

from .calibration import overconfidence_pattern, record_judgment
from .models import MetacognitiveJudgment


class _RecordJudgmentSerializer(serializers.Serializer):
    task_id = serializers.IntegerField()
    confidence_pre = serializers.IntegerField(min_value=1, max_value=5)
    judgment_type = serializers.ChoiceField(
        choices=MetacognitiveJudgment.JudgmentType.choices,
        default=MetacognitiveJudgment.JudgmentType.JOL,
    )

    def validate_task_id(self, value):
        if not MicroTask.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Unknown task_id.")
        return value


class CalibrationRecordView(APIView):
    permission_classes = (IsAuthenticated, IsStudent)

    def post(self, request):
        if not has_consent(request.user, "cognitive_calibration"):
            return Response(
                {"detail": "Bạn cần đồng ý 'cognitive_calibration' để dùng tính năng này.",
                 "consent_required": "cognitive_calibration"},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = _RecordJudgmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        task = MicroTask.objects.get(pk=data["task_id"])
        judgment = record_judgment(
            student=request.user,
            task=task,
            confidence_pre=data["confidence_pre"],
            judgment_type=data["judgment_type"],
        )
        return Response(
            {
                "id": judgment.id,
                "task_id": judgment.task_id,
                "confidence_pre": judgment.confidence_pre,
                "judgment_type": judgment.judgment_type,
                "created_at": judgment.created_at,
            },
            status=status.HTTP_201_CREATED,
        )


class MyCalibrationView(APIView):
    permission_classes = (IsAuthenticated, IsStudent)

    def get(self, request):
        if not has_consent(request.user, "cognitive_calibration"):
            return Response(
                {"detail": "Bạn cần đồng ý 'cognitive_calibration' để xem lịch sử.",
                 "consent_required": "cognitive_calibration"},
                status=status.HTTP_403_FORBIDDEN,
            )
        recent = list(
            MetacognitiveJudgment.objects.filter(student=request.user).order_by("-created_at")[:50]
        )
        diagnosis = overconfidence_pattern(recent)
        return Response({
            "diagnosis": diagnosis,
            "recent": [
                {
                    "id": j.id,
                    "task_id": j.task_id,
                    "confidence_pre": j.confidence_pre,
                    "actual_correct": j.actual_correct,
                    "calibration_error": j.calibration_error,
                    "judgment_type": j.judgment_type,
                    "created_at": j.created_at,
                }
                for j in recent
            ],
        })
