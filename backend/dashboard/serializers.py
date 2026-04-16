from rest_framework import serializers
from accounts.serializers import UserSerializer
from .models import Alert, InterventionAction


class AlertSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.get_full_name", read_only=True)
    student_username = serializers.CharField(source="student.username", read_only=True)
    concept_name = serializers.CharField(source="concept.name", read_only=True, default=None)
    milestone_title = serializers.CharField(source="milestone.title", read_only=True, default=None)

    class Meta:
        model = Alert
        fields = (
            "id", "student", "student_name", "student_username",
            "student_class", "severity", "status", "trigger_type",
            "concept", "concept_name", "milestone", "milestone_title",
            "reason", "evidence", "suggested_action",
            "dismiss_reason_code", "dismiss_note",
            "resolved_at", "expires_at", "created_at",
        )


class DismissAlertSerializer(serializers.Serializer):
    dismiss_reason_code = serializers.ChoiceField(choices=Alert.DismissReason.choices)
    dismiss_note = serializers.CharField(required=False, allow_blank=True, default="")


class InterventionActionSerializer(serializers.ModelSerializer):
    lecturer_name = serializers.CharField(source="lecturer.get_full_name", read_only=True)
    target_ids = serializers.PrimaryKeyRelatedField(
        source="targets", many=True, read_only=True,
    )

    class Meta:
        model = InterventionAction
        fields = (
            "id", "alert", "lecturer", "lecturer_name", "action_type",
            "target_ids", "message", "context", "follow_up_status",
            "created_at", "updated_at",
        )
        read_only_fields = ("lecturer", "created_at", "updated_at")


class CreateInterventionSerializer(serializers.Serializer):
    alert_id = serializers.IntegerField()
    action_type = serializers.ChoiceField(choices=InterventionAction.ActionType.choices)
    target_student_ids = serializers.ListField(child=serializers.IntegerField())
    message = serializers.CharField(required=False, allow_blank=True, default="")


class ClassOverviewSerializer(serializers.Serializer):
    total_students = serializers.IntegerField()
    on_track = serializers.IntegerField()
    needs_attention = serializers.IntegerField()
    needs_intervention = serializers.IntegerField()
    active_alerts = serializers.IntegerField()
    avg_mastery = serializers.FloatField()
    avg_completion_pct = serializers.FloatField()
    data_sufficient = serializers.BooleanField()
