"""DKT models — Phase 5 of v3 MAXIMAL roadmap.

Implements the storage for Deep Knowledge Tracing predictions, the
shadow-deployment comparison vs BKT v1/v2, and the per-attempt log we
need for offline training. The actual predictor lives in
``dkt/engine.py``; these models are intentionally model-agnostic so a
future PyTorch/Keras DKT can swap in without a migration.

Why we ship a NumPy SAKT-style predictor first instead of jumping
straight to PyTorch:

* Tests + CI run without the torch wheel (~2 GB, slow installs).
* Determinism (seeded NumPy) makes test assertions easier.
* Inference latency is microseconds for class sizes < 200, well within
  the SLO.

The model registry lives in ``mlops`` — a ``DKTModelVersion`` row here
points to a ``mlops.ModelVersion`` so promotion / shadow comparison
flows reuse the existing pipeline.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models


class DKTModelVersion(models.Model):
    """A trained DKT model snapshot.

    Today the only "trained" model is the deterministic NumPy
    predictor, but the row exists so when a real PyTorch model lands
    the registry can already point at it. ``mlops_version`` ties this
    to the existing model registry for promotion / shadow gating.
    """

    class Status(models.TextChoices):
        TRAINING = "training", "Đang huấn luyện"
        SHADOW = "shadow", "Đang shadow"
        STAGING = "staging", "Staging"
        PRODUCTION = "production", "Production"
        RETIRED = "retired", "Đã lưu trữ"

    name = models.CharField(max_length=80)
    semver = models.CharField(max_length=20, default="0.1.0")
    family = models.CharField(
        max_length=20,
        default="sakt-numpy",
        help_text="Engine family (sakt-numpy, dkt-pytorch, akt-pytorch, …)",
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.TRAINING,
    )

    mlops_version = models.ForeignKey(
        "mlops.ModelVersion",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="dkt_versions",
    )
    hyperparameters = models.JSONField(
        default=dict, blank=True,
        help_text="Engine hyperparameters captured at training time.",
    )
    metrics = models.JSONField(
        default=dict, blank=True,
        help_text="Offline validation metrics (auc, accuracy, calibration).",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    promoted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "palp_dkt_model_version"
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["family", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "semver"],
                name="uq_dkt_name_semver",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name}@{self.semver} [{self.status}]"


class DKTPrediction(models.Model):
    """Per-(student, concept) latest probability that the student answers correctly next.

    Stored snapshot rather than computed on every request because the
    inference is cheap but the read pattern (lecturer dashboard,
    pathway page) is frequent. Re-computed by
    ``dkt.tasks.refresh_predictions_periodic``.
    """

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dkt_predictions",
    )
    concept = models.ForeignKey(
        "curriculum.Concept",
        on_delete=models.CASCADE,
        related_name="dkt_predictions",
    )
    model_version = models.ForeignKey(
        DKTModelVersion,
        on_delete=models.CASCADE,
        related_name="predictions",
    )

    p_correct_next = models.FloatField(
        help_text="Probability the student answers the next item on this concept correctly.",
    )
    confidence = models.FloatField(
        default=0.5,
        help_text="0..1 — how confident the model is (sequence length / coverage).",
    )
    explanation = models.JSONField(
        default=dict, blank=True,
        help_text="Top-3 attention weights, recent attempts, prerequisite walks.",
    )

    computed_at = models.DateTimeField(auto_now=True)
    sequence_length = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "palp_dkt_prediction"
        ordering = ["-computed_at"]
        indexes = [
            models.Index(fields=["student", "concept"]),
            models.Index(fields=["model_version", "-computed_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "concept", "model_version"],
                name="uq_dkt_student_concept_version",
            ),
        ]

    def __str__(self) -> str:
        return f"DKT({self.student_id}, {self.concept_id})={self.p_correct_next:.3f}"


class DKTAttemptLog(models.Model):
    """One denormalised row per attempt the predictor consumes.

    Mirrors ``adaptive.TaskAttempt`` but in the denormalised shape the
    DKT engine wants: ``(student, concept, correct, ts)``. Keeping a
    separate table avoids forcing the adaptive app to expose its
    schema and lets us re-import historical adaptive attempts in a
    backfill job without locking adaptive.
    """

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dkt_attempts",
    )
    concept = models.ForeignKey(
        "curriculum.Concept",
        on_delete=models.CASCADE,
        related_name="dkt_attempts",
    )
    is_correct = models.BooleanField()
    response_time_seconds = models.FloatField(null=True, blank=True)
    hint_count = models.PositiveSmallIntegerField(default=0)
    occurred_at = models.DateTimeField()

    source_attempt_id = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_dkt_attempt_log"
        ordering = ["student", "occurred_at"]
        indexes = [
            models.Index(fields=["student", "occurred_at"]),
            models.Index(fields=["concept", "-occurred_at"]),
        ]

    def __str__(self) -> str:
        return f"DKTAttempt(s={self.student_id}, c={self.concept_id}, ok={self.is_correct})"
