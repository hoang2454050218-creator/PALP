from rest_framework import serializers

from .models import (
    CareerGoal,
    EffortRating,
    GoalReflection,
    SemesterGoal,
    StrategyEffectiveness,
    StrategyPlan,
    TimeEstimate,
    WeeklyGoal,
)


class CareerGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareerGoal
        fields = (
            "id", "label", "category", "horizon_months",
            "notes", "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class SemesterGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = SemesterGoal
        fields = (
            "id", "course", "semester", "mastery_target",
            "completion_target_pct", "intent",
            "started_at", "target_end", "is_active",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class StrategyPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = StrategyPlan
        fields = (
            "id", "weekly_goal", "strategy", "rationale",
            "predicted_minutes", "created_at",
        )
        read_only_fields = ("id", "created_at")


class WeeklyGoalSerializer(serializers.ModelSerializer):
    strategy_plans = StrategyPlanSerializer(many=True, read_only=True)

    class Meta:
        model = WeeklyGoal
        fields = (
            "id", "semester_goal", "week_start", "target_minutes",
            "target_concept_ids", "target_micro_task_count", "status",
            "drift_pct_last_check", "drift_last_checked_at",
            "strategy_plans", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "drift_pct_last_check", "drift_last_checked_at",
            "status", "strategy_plans", "created_at", "updated_at",
        )

    def validate_target_minutes(self, value):
        if value < 0 or value > 10080:
            raise serializers.ValidationError("target_minutes must be 0..10080.")
        return value


class TimeEstimateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeEstimate
        fields = (
            "id", "weekly_goal", "concept",
            "predicted_minutes", "actual_minutes",
            "estimate_error_pct", "created_at", "finalised_at",
        )
        read_only_fields = ("id", "estimate_error_pct", "created_at", "finalised_at")


class EffortRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = EffortRating
        fields = ("id", "weekly_goal", "rating", "note", "created_at")
        read_only_fields = ("id", "created_at")


class StrategyEffectivenessSerializer(serializers.ModelSerializer):
    class Meta:
        model = StrategyEffectiveness
        fields = (
            "id", "strategy_plan", "rating", "will_repeat",
            "note", "mastery_delta", "created_at",
        )
        read_only_fields = ("id", "mastery_delta", "created_at")


class GoalReflectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoalReflection
        fields = (
            "id", "weekly_goal", "week_start",
            "learned_text", "struggle_text", "next_priority_text",
            "submitted_at", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "weekly_goal", "week_start",
            "submitted_at", "created_at", "updated_at",
        )


class _StrategyEffectivenessInputSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    will_repeat = serializers.BooleanField(required=False, default=False)
    note = serializers.CharField(required=False, allow_blank=True, default="")


class ReflectionSubmitSerializer(serializers.Serializer):
    weekly_goal_id = serializers.IntegerField()
    learned_text = serializers.CharField(required=False, allow_blank=True, default="")
    struggle_text = serializers.CharField(required=False, allow_blank=True, default="")
    next_priority_text = serializers.CharField(required=False, allow_blank=True, default="")
    effort_rating = serializers.IntegerField(min_value=1, max_value=5, required=False, allow_null=True)
    effort_note = serializers.CharField(required=False, allow_blank=True, default="")
    strategy_effectiveness = serializers.DictField(
        child=_StrategyEffectivenessInputSerializer(),
        required=False,
    )

    def validate_strategy_effectiveness(self, value):
        # Coerce string keys (JSON) to int
        if not value:
            return {}
        return {int(k): v for k, v in value.items()}
