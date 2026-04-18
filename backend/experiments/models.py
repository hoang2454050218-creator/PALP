"""
A/B testing primitives for pedagogical experiments.

Researchers define an Experiment with multiple Variants. The first time a
user hits an experiment they get a sticky Assignment (deterministic hash
of user id + experiment) so behaviour stays consistent across navigations.

Variant id is auto-injected into ``EventLog.properties.experiment_assignments``
by ``experiments.middleware.AssignmentMiddleware`` so analytics can slice
KPIs by variant without app code changes.
"""
from django.conf import settings
from django.db import models


class Experiment(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Nháp"
        RUNNING = "running", "Đang chạy"
        PAUSED = "paused", "Tạm dừng"
        ENDED = "ended", "Đã kết thúc"

    class MetricKind(models.TextChoices):
        NUMERIC = "numeric", "Số (Welch's t-test)"
        BINARY = "binary", "Nhị phân (chi-square)"

    name = models.SlugField(max_length=80, unique=True)
    hypothesis = models.TextField(
        help_text="Giả thuyết khoa học mà thí nghiệm cần xác minh."
    )
    primary_metric = models.CharField(
        max_length=80,
        help_text="Tên KPI chính, ví dụ 'micro_task_completion_rate'.",
    )
    metric_kind = models.CharField(
        max_length=10, choices=MetricKind.choices, default=MetricKind.NUMERIC,
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_experiment"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"[{self.status}] {self.name}"


class ExperimentVariant(models.Model):
    experiment = models.ForeignKey(
        Experiment, on_delete=models.CASCADE, related_name="variants",
    )
    name = models.CharField(max_length=40, help_text="ví dụ: control, treatment_a")
    weight = models.PositiveSmallIntegerField(
        default=50,
        help_text="Tổng weight các variant phải bằng 100 cho 1 experiment.",
    )
    config_json = models.JSONField(
        default=dict, blank=True,
        help_text="Cấu hình variant (rules, copy, threshold).",
    )

    class Meta:
        db_table = "palp_experiment_variant"
        constraints = [
            models.UniqueConstraint(
                fields=["experiment", "name"],
                name="uq_variant_experiment_name",
            ),
        ]
        ordering = ["experiment", "name"]

    def __str__(self) -> str:
        return f"{self.experiment.name}:{self.name} ({self.weight}%)"


class ExperimentAssignment(models.Model):
    experiment = models.ForeignKey(
        Experiment, on_delete=models.CASCADE, related_name="assignments",
    )
    variant = models.ForeignKey(
        ExperimentVariant, on_delete=models.CASCADE, related_name="assignments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="experiment_assignments",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_experiment_assignment"
        constraints = [
            models.UniqueConstraint(
                fields=["experiment", "user"],
                name="uq_assignment_experiment_user",
            ),
        ]
        indexes = [
            models.Index(fields=["experiment", "variant"]),
            models.Index(fields=["user", "experiment"]),
        ]
