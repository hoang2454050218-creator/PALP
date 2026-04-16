from rest_framework import serializers
from django.conf import settings
from .models import MasteryState, TaskAttempt, ContentIntervention, StudentPathway, PathwayOverride


class MasteryStateSerializer(serializers.ModelSerializer):
    """Full mastery data for admin views."""
    concept_name = serializers.CharField(source="concept.name", read_only=True)

    class Meta:
        model = MasteryState
        fields = (
            "id", "concept", "concept_name", "p_mastery",
            "attempt_count", "correct_count", "last_updated",
        )


class LecturerMasteryStateSerializer(serializers.ModelSerializer):
    """Lecturer-scoped: pedagogically relevant fields only, no BKT internals."""
    concept_name = serializers.CharField(source="concept.name", read_only=True)
    mastery_level = serializers.CharField(read_only=True)

    class Meta:
        model = MasteryState
        fields = (
            "id", "concept", "concept_name", "p_mastery",
            "mastery_level", "attempt_count", "correct_count",
            "last_updated",
        )


class StudentMasteryStateSerializer(serializers.ModelSerializer):
    """Student-safe mastery view: no raw p_mastery, only qualitative labels."""
    concept_name = serializers.CharField(source="concept.name", read_only=True)
    mastery_level = serializers.CharField(read_only=True)
    mastery_label = serializers.CharField(source="student_facing_label", read_only=True)
    progress_indicator = serializers.SerializerMethodField()

    class Meta:
        model = MasteryState
        fields = (
            "id", "concept", "concept_name",
            "mastery_level", "mastery_label", "progress_indicator",
            "attempt_count", "last_updated",
        )

    def get_progress_indicator(self, obj):
        thresholds = settings.PALP_ADAPTIVE_THRESHOLDS
        low = thresholds["MASTERY_LOW"]
        high = thresholds["MASTERY_HIGH"]

        if obj.p_mastery >= high:
            return 100
        if obj.p_mastery <= 0.01:
            return 0
        if obj.p_mastery >= low:
            return round(60 + (obj.p_mastery - low) / (high - low) * 40)
        return round(obj.p_mastery / low * 60)


class TaskAttemptSerializer(serializers.ModelSerializer):
    task_title = serializers.CharField(source="task.title", read_only=True)

    class Meta:
        model = TaskAttempt
        fields = (
            "id", "task", "task_title", "score", "max_score",
            "duration_seconds", "hints_used", "is_correct",
            "answer", "attempt_number", "created_at",
        )
        read_only_fields = ("is_correct", "attempt_number", "created_at")


class SubmitTaskSerializer(serializers.Serializer):
    task_id = serializers.IntegerField()
    answer = serializers.JSONField()
    duration_seconds = serializers.IntegerField(min_value=0)
    hints_used = serializers.IntegerField(min_value=0, default=0)


class ContentInterventionSerializer(serializers.ModelSerializer):
    concept_name = serializers.CharField(source="concept.name", read_only=True)

    class Meta:
        model = ContentIntervention
        fields = (
            "id", "concept", "concept_name", "intervention_type",
            "source_rule", "rule_version", "p_mastery_at_trigger",
            "mastery_before", "mastery_after", "explanation",
            "was_helpful", "created_at",
        )


class StudentPathwaySerializer(serializers.ModelSerializer):
    current_concept_name = serializers.CharField(source="current_concept.name", read_only=True, default=None)
    current_milestone_title = serializers.CharField(source="current_milestone.title", read_only=True, default=None)
    progress_pct = serializers.SerializerMethodField()
    concepts_needing_review = serializers.SerializerMethodField()

    class Meta:
        model = StudentPathway
        fields = (
            "id", "course", "current_concept", "current_concept_name",
            "current_milestone", "current_milestone_title",
            "current_difficulty", "concepts_completed",
            "milestones_completed", "progress_pct",
            "concepts_needing_review", "updated_at",
        )

    def get_progress_pct(self, obj):
        """Live mastery-based progress instead of one-time completion snapshot."""
        total = obj.course.concepts.filter(is_active=True).count()
        if total == 0:
            return 0
        mastered = MasteryState.objects.filter(
            student=obj.student,
            concept__course=obj.course,
            concept__is_active=True,
            p_mastery__gte=settings.PALP_ADAPTIVE_THRESHOLDS["MASTERY_HIGH"],
        ).count()
        return round(mastered / total * 100, 1)

    def get_concepts_needing_review(self, obj):
        """Concepts that were once completed but mastery has since decayed."""
        if not obj.concepts_completed:
            return []
        decayed = MasteryState.objects.filter(
            student=obj.student,
            concept_id__in=obj.concepts_completed,
            p_mastery__lt=settings.PALP_ADAPTIVE_THRESHOLDS["MASTERY_HIGH"],
        ).select_related("concept").values_list("concept__name", flat=True)
        return list(decayed)


class PathwayOverrideSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source="student.username", read_only=True)
    lecturer_name = serializers.CharField(source="lecturer.get_full_name", read_only=True)

    class Meta:
        model = PathwayOverride
        fields = (
            "id", "student", "student_username", "course",
            "lecturer", "lecturer_name",
            "override_type", "reason", "parameters",
            "is_active", "applied_at", "expires_at",
        )
        read_only_fields = ("lecturer", "applied_at")


class CreateOverrideSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    course_id = serializers.IntegerField()
    override_type = serializers.ChoiceField(choices=PathwayOverride.OverrideType.choices)
    reason = serializers.CharField(min_length=5)
    parameters = serializers.JSONField(default=dict)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
