from django.contrib import admin
from .models import Assessment, AssessmentQuestion, AssessmentSession, AssessmentResponse, LearnerProfile


class AssessmentQuestionInline(admin.TabularInline):
    model = AssessmentQuestion
    extra = 1


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "time_limit_minutes", "is_active")
    inlines = [AssessmentQuestionInline]


@admin.register(AssessmentSession)
class AssessmentSessionAdmin(admin.ModelAdmin):
    list_display = ("student", "assessment", "status", "total_score", "started_at")
    list_filter = ("status",)


@admin.register(LearnerProfile)
class LearnerProfileAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "overall_score", "created_at")
