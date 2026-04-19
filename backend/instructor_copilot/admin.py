from django.contrib import admin

from instructor_copilot.models import FeedbackDraft, GeneratedExercise


@admin.register(GeneratedExercise)
class GeneratedExerciseAdmin(admin.ModelAdmin):
    list_display = (
        "id", "course", "concept", "title",
        "difficulty", "status", "requested_by", "created_at",
    )
    list_filter = ("status", "difficulty", "template_key")
    raw_id_fields = ("course", "concept", "requested_by")
    search_fields = ("title",)


@admin.register(FeedbackDraft)
class FeedbackDraftAdmin(admin.ModelAdmin):
    list_display = (
        "id", "student", "week_start", "status",
        "requested_by", "created_at", "sent_at",
    )
    list_filter = ("status",)
    raw_id_fields = ("student", "requested_by")
