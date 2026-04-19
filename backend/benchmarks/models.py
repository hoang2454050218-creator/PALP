"""External benchmark models — Phase 7 of v3 MAXIMAL roadmap.

Stores the metadata + per-run results for evaluating PALP's KT
predictors against the standard public benchmarks the academic
community uses (EdNet, ASSISTments, …). The actual loaders +
evaluators live in ``benchmarks/services.py``.

Why we ship a benchmark *infrastructure* rather than just the result
numbers:

* Reproducibility: each ``BenchmarkRun`` captures the model version,
  dataset slice, hyperparameters, and seed; running it again produces
  the same numbers.
* Drift watch: comparing ``BenchmarkResult`` over time tells us when
  a model regression sneaks in.
* Publication packaging: the result table is exactly what the
  reproducibility kit (Phase 7 ``publication`` app) reads.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models


class BenchmarkDataset(models.Model):
    """One curated public dataset (or a synthetic stand-in).

    We deliberately do NOT ship raw EdNet / ASSISTments rows in the
    repo — those datasets carry their own licences. The
    ``loader_path`` column points to the loader function the
    evaluator imports; if the file isn't present we fall back to the
    deterministic synthetic generator so tests stay green offline.
    """

    class Source(models.TextChoices):
        EDNET = "ednet", "EdNet (RIIID)"
        ASSISTMENTS_2009 = "assistments_2009", "ASSISTments 2009"
        ASSISTMENTS_2017 = "assistments_2017", "ASSISTments 2017"
        STATICS_2011 = "statics_2011", "STATICS 2011"
        SYNTHETIC = "synthetic", "Synthetic (deterministic)"
        OTHER = "other", "Khác"

    key = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=160)
    source = models.CharField(max_length=24, choices=Source.choices)
    description = models.TextField(blank=True)
    license = models.CharField(max_length=80, blank=True)
    loader_path = models.CharField(
        max_length=200, blank=True,
        help_text="Dotted import path of the loader function (returns iterable of attempts).",
    )
    students = models.PositiveIntegerField(default=0)
    concepts = models.PositiveIntegerField(default=0)
    interactions = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_benchmark_dataset"
        ordering = ["source", "key"]

    def __str__(self) -> str:
        return f"{self.key} ({self.source})"


class BenchmarkRun(models.Model):
    """One evaluation run of a specific model on a specific dataset slice."""

    class Status(models.TextChoices):
        PENDING = "pending", "Đang chờ"
        RUNNING = "running", "Đang chạy"
        SUCCESS = "success", "Thành công"
        FAILED = "failed", "Lỗi"

    dataset = models.ForeignKey(
        BenchmarkDataset,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    model_label = models.CharField(
        max_length=120,
        help_text="Free-form label, e.g. 'sakt-numpy@0.1.0' or 'bkt@v1'.",
    )
    model_family = models.CharField(max_length=40, blank=True)
    seed = models.PositiveIntegerField(default=42)
    sample_size = models.PositiveIntegerField(default=0)
    hyperparameters = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)

    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="benchmark_runs",
    )

    class Meta:
        db_table = "palp_benchmark_run"
        indexes = [
            models.Index(fields=["dataset", "-started_at"]),
            models.Index(fields=["status", "-started_at"]),
        ]

    def __str__(self) -> str:
        return f"Run({self.model_label}) on {self.dataset.key} [{self.status}]"


class BenchmarkResult(models.Model):
    """One metric × one run."""

    run = models.ForeignKey(
        BenchmarkRun, on_delete=models.CASCADE, related_name="results",
    )
    metric_key = models.CharField(max_length=40)
    value = models.FloatField()
    notes = models.CharField(max_length=240, blank=True)

    class Meta:
        db_table = "palp_benchmark_result"
        constraints = [
            models.UniqueConstraint(
                fields=["run", "metric_key"],
                name="uq_benchmark_run_metric",
            ),
        ]
        indexes = [
            models.Index(fields=["metric_key"]),
        ]

    def __str__(self) -> str:
        return f"{self.run_id}/{self.metric_key}={self.value:.4f}"
