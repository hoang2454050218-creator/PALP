from django.contrib import admin
from .models import (
    Course, Enrollment, Concept, ConceptPrerequisite,
    Milestone, MicroTask, SupplementaryContent,
)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "credits", "is_active")


@admin.register(Concept)
class ConceptAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "course", "order", "is_active")
    list_filter = ("course",)


@admin.register(ConceptPrerequisite)
class ConceptPrerequisiteAdmin(admin.ModelAdmin):
    list_display = ("concept", "prerequisite")


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "order", "target_week")
    list_filter = ("course",)


@admin.register(MicroTask)
class MicroTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "milestone", "concept", "difficulty", "task_type", "estimated_minutes")
    list_filter = ("difficulty", "task_type", "milestone")


@admin.register(SupplementaryContent)
class SupplementaryContentAdmin(admin.ModelAdmin):
    list_display = ("title", "concept", "content_type", "difficulty_target")


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "semester", "is_active")
