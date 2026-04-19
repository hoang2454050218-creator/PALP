from django.contrib import admin
from .models import (
    ContentIntervention,
    MasteryState,
    MetacognitiveJudgment,
    PathwayOverride,
    StudentPathway,
    TaskAttempt,
)


@admin.register(MasteryState)
class MasteryStateAdmin(admin.ModelAdmin):
    list_display = ("student", "concept", "p_mastery", "attempt_count", "correct_count", "last_updated")
    list_filter = ("concept__course",)


@admin.register(TaskAttempt)
class TaskAttemptAdmin(admin.ModelAdmin):
    list_display = ("student", "task", "score", "is_correct", "attempt_number", "created_at")
    list_filter = ("is_correct",)


@admin.register(ContentIntervention)
class ContentInterventionAdmin(admin.ModelAdmin):
    list_display = ("student", "concept", "intervention_type", "source_rule", "p_mastery_at_trigger", "created_at")
    list_filter = ("intervention_type",)


@admin.register(StudentPathway)
class StudentPathwayAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "current_concept", "current_difficulty", "updated_at")


@admin.register(PathwayOverride)
class PathwayOverrideAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "lecturer", "override_type", "is_active", "applied_at")
    list_filter = ("override_type", "is_active")


@admin.register(MetacognitiveJudgment)
class MetacognitiveJudgmentAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "task",
        "confidence_pre",
        "actual_correct",
        "calibration_error",
        "judgment_type",
        "created_at",
    )
    list_filter = ("judgment_type", "actual_correct")
    search_fields = ("student__username", "task__title")
    readonly_fields = ("created_at", "calibration_error")
