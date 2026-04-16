from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from accounts.permissions import IsStudent, IsLecturerOrAdmin, IsStudentInLecturerClass
from events.services import audit_log
from events.models import EventLog
from .models import Assessment, AssessmentSession, LearnerProfile
from .serializers import (
    AssessmentSerializer, AssessmentQuestionSerializer,
    AssessmentSessionSerializer, LearnerProfileSerializer,
    SubmitAnswerSerializer,
)
from .services import submit_answer, complete_assessment, check_session_timeout
from palp.idempotency import idempotent
from palp.throttles import AssessmentSubmitThrottle


class AssessmentListView(generics.ListAPIView):
    serializer_class = AssessmentSerializer

    def get_queryset(self):
        return Assessment.objects.filter(is_active=True)


class AssessmentQuestionsView(generics.ListAPIView):
    serializer_class = AssessmentQuestionSerializer

    def get_queryset(self):
        assessment = get_object_or_404(Assessment, id=self.kwargs["pk"])
        return assessment.questions.all().order_by("order")


class StartAssessmentView(APIView):
    permission_classes = (IsStudent,)

    @idempotent(required=True)
    def post(self, request, pk):
        assessment = get_object_or_404(Assessment, id=pk, is_active=True)

        existing = AssessmentSession.objects.filter(
            student=request.user,
            assessment=assessment,
            status=AssessmentSession.Status.IN_PROGRESS,
        ).first()

        if existing:
            if existing.is_expired:
                existing.status = AssessmentSession.Status.EXPIRED
                existing.save(update_fields=["status"])
            else:
                answered_ids = list(
                    existing.responses.values_list("question_id", flat=True)
                )
                audit_log(
                    request.user,
                    EventLog.EventName.ASSESS_RESUMED,
                    {"session_id": existing.id, "answered_count": len(answered_ids)},
                )
                data = AssessmentSessionSerializer(existing).data
                data["answered_question_ids"] = answered_ids
                data["server_now"] = timezone.now().isoformat()
                return Response(data, status=status.HTTP_200_OK)

        session = AssessmentSession.objects.create(
            student=request.user, assessment=assessment
        )
        data = AssessmentSessionSerializer(session).data
        data["answered_question_ids"] = []
        data["server_now"] = timezone.now().isoformat()
        return Response(data, status=status.HTTP_201_CREATED)


class SubmitAnswerView(APIView):
    permission_classes = (IsStudent,)
    throttle_classes = (AssessmentSubmitThrottle,)

    @idempotent(required=True)
    def post(self, request, session_id):
        session = get_object_or_404(
            AssessmentSession.objects.select_related("assessment"),
            id=session_id,
            student=request.user,
        )
        check_session_timeout(session)

        serializer = SubmitAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        client_version = serializer.validated_data.get("client_version")

        response = submit_answer(
            session,
            serializer.validated_data["question_id"],
            serializer.validated_data["answer"],
            serializer.validated_data["time_taken_seconds"],
            client_version=client_version,
        )

        current_version = AssessmentSession.objects.values_list(
            "version", flat=True
        ).get(id=session_id)

        return Response(
            {
                "is_correct": response.is_correct,
                "response_id": response.id,
                "version": current_version,
            },
            status=status.HTTP_200_OK,
        )


class CompleteAssessmentView(APIView):
    permission_classes = (IsStudent,)

    @idempotent(required=True)
    def post(self, request, session_id):
        profile = complete_assessment(session_id, request.user.id)
        session = AssessmentSession.objects.select_related("assessment").get(id=session_id)
        return Response(
            {
                "session": AssessmentSessionSerializer(session).data,
                "profile": LearnerProfileSerializer(profile).data,
            },
            status=status.HTTP_200_OK,
        )


class MyAssessmentSessionsView(generics.ListAPIView):
    serializer_class = AssessmentSessionSerializer
    permission_classes = (IsStudent,)

    def get_queryset(self):
        return AssessmentSession.objects.filter(
            student=self.request.user
        ).select_related("assessment").order_by("-started_at")


class LearnerProfileView(generics.RetrieveAPIView):
    serializer_class = LearnerProfileSerializer

    def get_object(self):
        return get_object_or_404(
            LearnerProfile,
            student=self.request.user,
            course_id=self.kwargs["course_id"],
        )


class StudentLearnerProfileView(generics.RetrieveAPIView):
    serializer_class = LearnerProfileSerializer
    permission_classes = (IsLecturerOrAdmin, IsStudentInLecturerClass)

    def get_object(self):
        return get_object_or_404(
            LearnerProfile,
            student_id=self.kwargs["student_id"],
            course_id=self.kwargs["course_id"],
        )
