from django.contrib import admin

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


@admin.register(CareerGoal)
class CareerGoalAdmin(admin.ModelAdmin):
    list_display = ("student", "label", "category", "horizon_months", "updated_at")
    list_filter = ("category",)
    search_fields = ("student__username", "label")
    readonly_fields = ("created_at", "updated_at")


@admin.register(SemesterGoal)
class SemesterGoalAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "semester", "mastery_target", "is_active", "started_at")
    list_filter = ("is_active", "semester")
    search_fields = ("student__username", "course__code")


@admin.register(WeeklyGoal)
class WeeklyGoalAdmin(admin.ModelAdmin):
    list_display = ("student", "week_start", "target_minutes", "target_micro_task_count", "status", "drift_pct_last_check")
    list_filter = ("status", "week_start")
    search_fields = ("student__username",)
    date_hierarchy = "week_start"
    readonly_fields = ("drift_pct_last_check", "drift_last_checked_at", "created_at", "updated_at")


@admin.register(StrategyPlan)
class StrategyPlanAdmin(admin.ModelAdmin):
    list_display = ("weekly_goal", "strategy", "predicted_minutes", "created_at")
    list_filter = ("strategy",)


@admin.register(TimeEstimate)
class TimeEstimateAdmin(admin.ModelAdmin):
    list_display = ("student", "weekly_goal", "concept", "predicted_minutes", "actual_minutes", "estimate_error_pct", "created_at")
    list_filter = ("finalised_at",)


@admin.register(GoalReflection)
class GoalReflectionAdmin(admin.ModelAdmin):
    list_display = ("student", "week_start", "submitted_at")
    search_fields = ("student__username",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "week_start"


@admin.register(EffortRating)
class EffortRatingAdmin(admin.ModelAdmin):
    list_display = ("student", "weekly_goal", "rating", "created_at")
    list_filter = ("rating",)


@admin.register(StrategyEffectiveness)
class StrategyEffectivenessAdmin(admin.ModelAdmin):
    list_display = ("student", "strategy_plan", "rating", "will_repeat", "mastery_delta", "created_at")
    list_filter = ("rating", "will_repeat")
