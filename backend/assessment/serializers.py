from rest_framework import serializers
from .models import (
    Assessment, AssessmentQuestion, AssessmentSession,
    AssessmentResponse, LearnerProfile,
)


class AssessmentQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentQuestion
        fields = ("id", "concept", "question_type", "text", "options", "order", "points")


class AssessmentQuestionDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentQuestion
        fields = (
            "id", "concept", "question_type", "text", "options",
            "correct_answer", "explanation", "order", "points",
        )


class AssessmentSerializer(serializers.ModelSerializer):
    question_count = serializers.SerializerMethodField()

    class Meta:
        model = Assessment
        fields = ("id", "course", "title", "description", "time_limit_minutes", "question_count")

    def get_question_count(self, obj):
        return obj.questions.count()


class AssessmentResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentResponse
        fields = ("id", "question", "answer", "is_correct", "time_taken_seconds")
        read_only_fields = ("is_correct",)


class SubmitAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    answer = serializers.JSONField()
    time_taken_seconds = serializers.IntegerField(min_value=0)
    client_version = serializers.IntegerField(required=False, default=None)


class AssessmentSessionSerializer(serializers.ModelSerializer):
    responses = AssessmentResponseSerializer(many=True, read_only=True)
    assessment_title = serializers.CharField(source="assessment.title", read_only=True)

    class Meta:
        model = AssessmentSession
        fields = (
            "id", "assessment", "assessment_title", "status", "version",
            "started_at", "completed_at", "submitted_at",
            "total_score", "total_time_seconds", "responses",
        )
        read_only_fields = (
            "status", "version", "started_at", "completed_at",
            "submitted_at", "total_score", "total_time_seconds",
        )


class LearnerProfileSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.get_full_name", read_only=True)

    class Meta:
        model = LearnerProfile
        fields = (
            "id", "student", "student_name", "course", "overall_score",
            "initial_mastery", "strengths", "weaknesses",
            "recommended_start_concept", "created_at", "updated_at",
        )
        read_only_fields = fields
