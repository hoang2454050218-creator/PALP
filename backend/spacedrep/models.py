"""Spaced Repetition models — Phase 6 of v3 MAXIMAL roadmap.

Implements the storage for FSRS-4.5 (Free Spaced Repetition Scheduler).
The scheduler itself is in ``spacedrep/engine.py``; these models hold
the per-card memory state + the review history we need to fit
parameters offline.

Why FSRS over SM-2 / Leitner:

* Learns per-user weights (we ship the official defaults; the trainer
  is a Phase 6B follow-up).
* Stability + Difficulty + Retrievability are first-class — we can
  expose them in the UI ("70% retrievability, due in 4 days").
* Open-source community has validated parameter sets we can fall back
  to if a user has too few reviews to fit their own.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models


class ReviewItem(models.Model):
    """A single thing the student is being asked to remember.

    Today an item is always a Concept; future shapes (vocabulary card,
    formula, worked example) can land here without a migration via
    ``payload``.
    """

    class State(models.TextChoices):
        NEW = "new", "Mới"
        LEARNING = "learning", "Đang học"
        REVIEW = "review", "Đang ôn"
        RELEARNING = "relearning", "Học lại"
        SUSPENDED = "suspended", "Tạm dừng"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="review_items",
    )
    concept = models.ForeignKey(
        "curriculum.Concept",
        on_delete=models.CASCADE,
        related_name="review_items",
    )
    state = models.CharField(
        max_length=16, choices=State.choices, default=State.NEW,
    )
    payload = models.JSONField(default=dict, blank=True)

    # FSRS memory state
    stability = models.FloatField(
        default=1.0,
        help_text="FSRS stability (days). Higher = forgets slower.",
    )
    difficulty = models.FloatField(
        default=5.0,
        help_text="FSRS difficulty 1..10. Higher = harder for THIS student.",
    )
    last_review_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    review_count = models.PositiveIntegerField(default=0)
    lapse_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_spacedrep_item"
        indexes = [
            models.Index(fields=["student", "due_at"]),
            models.Index(fields=["student", "state"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "concept"],
                name="uq_review_item_student_concept",
            ),
        ]

    def __str__(self) -> str:
        return f"ReviewItem(s={self.student_id}, c={self.concept_id}, {self.state})"


class ReviewLog(models.Model):
    """Append-only history — what the student rated, what FSRS decided next."""

    class Rating(models.IntegerChoices):
        AGAIN = 1, "Quên hẳn"
        HARD = 2, "Vất vả"
        GOOD = 3, "Tốt"
        EASY = 4, "Dễ"

    item = models.ForeignKey(
        ReviewItem, on_delete=models.CASCADE, related_name="logs",
    )
    rating = models.PositiveSmallIntegerField(choices=Rating.choices)
    response_time_seconds = models.FloatField(null=True, blank=True)

    pre_stability = models.FloatField()
    pre_difficulty = models.FloatField()
    post_stability = models.FloatField()
    post_difficulty = models.FloatField()
    interval_days = models.FloatField()
    retrievability_at_review = models.FloatField(default=0.0)

    reviewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_spacedrep_log"
        ordering = ["item", "reviewed_at"]
        indexes = [
            models.Index(fields=["item", "-reviewed_at"]),
        ]

    def __str__(self) -> str:
        return f"ReviewLog(item={self.item_id}, r={self.rating}, ivl={self.interval_days:.1f}d)"
