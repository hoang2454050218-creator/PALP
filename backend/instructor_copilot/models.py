"""Instructor Co-pilot models — Phase 6 of v3 MAXIMAL roadmap.

Stores artefacts the lecturer-side helpers produce — auto-generated
exercise drafts, feedback summaries, content-review notes — *before*
they are approved and published. Approval is always a human step;
nothing here can mutate ``curriculum.MicroTask`` directly.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models


class GeneratedExercise(models.Model):
    """A draft exercise (multi-choice today; richer payloads next).

    Pre-publication. Lecturer reviews, edits, and approves; on approval
    a real ``curriculum.MicroTask`` row is created via the service
    layer.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Bản nháp"
        REVIEWED = "reviewed", "Đã review"
        APPROVED = "approved", "Đã duyệt"
        REJECTED = "rejected", "Đã từ chối"
        PUBLISHED = "published", "Đã xuất bản"

    class Difficulty(models.IntegerChoices):
        EASY = 1, "Dễ"
        MEDIUM = 2, "Trung bình"
        HARD = 3, "Khó"

    course = models.ForeignKey(
        "curriculum.Course",
        on_delete=models.CASCADE,
        related_name="generated_exercises",
    )
    concept = models.ForeignKey(
        "curriculum.Concept",
        on_delete=models.CASCADE,
        related_name="generated_exercises",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="generated_exercises",
    )
    template_key = models.SlugField(max_length=80)
    difficulty = models.PositiveSmallIntegerField(
        choices=Difficulty.choices, default=Difficulty.MEDIUM,
    )

    title = models.CharField(max_length=200)
    body = models.JSONField(
        default=dict,
        help_text="{question, options, correct_answer, hints, explanation}",
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT,
    )
    review_notes = models.TextField(blank=True)
    published_micro_task_id = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_copilot_generated_exercise"
        indexes = [
            models.Index(fields=["course", "concept", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"GenEx({self.id}, {self.concept_id}, {self.status})"


class FeedbackDraft(models.Model):
    """Lecturer-facing feedback draft for one (student, week) pair."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Bản nháp"
        SENT = "sent", "Đã gửi"
        ARCHIVED = "archived", "Đã lưu trữ"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="feedback_drafts_received",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="feedback_drafts_authored",
    )
    week_start = models.DateField()
    summary = models.TextField()
    highlights = models.JSONField(default=list, blank=True)
    concerns = models.JSONField(default=list, blank=True)
    suggestions = models.JSONField(default=list, blank=True)

    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT,
    )
    sent_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_copilot_feedback_draft"
        indexes = [
            models.Index(fields=["student", "-week_start"]),
            models.Index(fields=["status", "-created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "week_start", "requested_by"],
                name="uq_feedback_draft_student_week_author",
            ),
        ]

    def __str__(self) -> str:
        return f"FBDraft({self.student_id}, {self.week_start}, {self.status})"
