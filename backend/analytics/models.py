import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class KPIDefinition(models.Model):
    SCHEMA_VERSION = "1.0"

    LOCKED_FIELDS = frozenset({
        "code", "source_events", "query_function", "query_sql",
        "target_value", "target_direction", "unit",
    })

    class TargetDirection(models.TextChoices):
        INCREASE = "increase", "Tăng"
        DECREASE = "decrease", "Giảm"
        ABSOLUTE = "absolute", "Đạt ngưỡng"

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_kpis",
    )
    description = models.TextField()
    unit = models.CharField(max_length=50)
    target_value = models.FloatField()
    target_direction = models.CharField(
        max_length=10, choices=TargetDirection.choices,
    )
    source_events = models.JSONField(default=list, blank=True)
    query_function = models.CharField(max_length=200)
    query_sql = models.TextField(blank=True)
    baseline_value = models.FloatField(null=True, blank=True)
    baseline_locked_at = models.DateTimeField(null=True, blank=True)
    baseline_period_start = models.DateTimeField(null=True, blank=True)
    baseline_period_end = models.DateTimeField(null=True, blank=True)
    intervention_period_start = models.DateTimeField(null=True, blank=True)
    intervention_period_end = models.DateTimeField(null=True, blank=True)
    is_locked = models.BooleanField(default=False)
    current_version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_kpi_definition"
        ordering = ["code"]

    def __str__(self):
        lock = " [LOCKED]" if self.is_locked else ""
        return f"{self.code} v{self.current_version}{lock}"

    def clean(self):
        if self.baseline_period_start and self.baseline_period_end:
            if self.baseline_period_start >= self.baseline_period_end:
                raise ValidationError("baseline_period_start must precede baseline_period_end.")
        if self.intervention_period_start and self.intervention_period_end:
            if self.intervention_period_start >= self.intervention_period_end:
                raise ValidationError("intervention_period_start must precede intervention_period_end.")
        if (
            self.baseline_period_end
            and self.intervention_period_start
            and self.baseline_period_end > self.intervention_period_start
        ):
            raise ValidationError("Baseline and intervention periods must not overlap.")

    def save(self, **kwargs):
        self.full_clean()
        if self.pk:
            self._enforce_lock()
        super().save(**kwargs)

    def _enforce_lock(self):
        if not self.is_locked:
            return
        try:
            old = KPIDefinition.objects.get(pk=self.pk)
        except KPIDefinition.DoesNotExist:
            return
        changed = [
            f for f in self.LOCKED_FIELDS
            if getattr(self, f) != getattr(old, f)
        ]
        if changed:
            raise ValidationError(
                f"KPI '{self.code}' is locked. Cannot modify: {', '.join(changed)}."
            )

    def snapshot_dict(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "owner_id": self.owner_id,
            "description": self.description,
            "unit": self.unit,
            "target_value": self.target_value,
            "target_direction": self.target_direction,
            "source_events": self.source_events,
            "query_function": self.query_function,
            "query_sql": self.query_sql,
            "baseline_value": self.baseline_value,
            "current_version": self.current_version,
        }

    def bump_version(self, change_reason: str, changed_by):
        snapshot = self.snapshot_dict()
        KPIVersion.objects.create(
            kpi=self,
            version=self.current_version,
            definition_snapshot=snapshot,
            change_reason=change_reason,
            created_by=changed_by,
        )
        self.current_version += 1
        super().save(update_fields=["current_version", "updated_at"])


class KPIVersion(models.Model):
    kpi = models.ForeignKey(
        KPIDefinition, on_delete=models.CASCADE, related_name="versions",
    )
    version = models.PositiveIntegerField()
    definition_snapshot = models.JSONField()
    change_reason = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_kpi_version"
        unique_together = [("kpi", "version")]
        ordering = ["kpi", "-version"]

    def __str__(self):
        return f"{self.kpi.code} v{self.version}"


class KPILineageLog(models.Model):
    kpi = models.ForeignKey(
        KPIDefinition, on_delete=models.CASCADE, related_name="lineage_logs",
    )
    report = models.ForeignKey(
        "PilotReport", on_delete=models.CASCADE,
        null=True, blank=True, related_name="lineage_logs",
    )
    week_number = models.PositiveSmallIntegerField()
    class_id = models.PositiveIntegerField()
    computed_value = models.FloatField()
    event_count = models.PositiveIntegerField(default=0)
    event_date_range = models.JSONField(default=dict)
    sample_event_ids = models.JSONField(default=list)
    computation_params = models.JSONField(default=dict)
    data_quality_flags = models.JSONField(default=dict)
    definition_version = models.PositiveIntegerField()
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_kpi_lineage_log"
        ordering = ["-computed_at"]

    def __str__(self):
        return f"{self.kpi.code} W{self.week_number} = {self.computed_value}"


class PilotReport(models.Model):
    class ReportType(models.TextChoices):
        WEEKLY = "weekly", "Tuần"
        MILESTONE = "milestone", "Mốc báo cáo"
        FINAL = "final", "Báo cáo cuối"

    title = models.CharField(max_length=200)
    report_type = models.CharField(max_length=15, choices=ReportType.choices)
    week_number = models.PositiveSmallIntegerField(null=True, blank=True)
    schema_version = models.CharField(max_length=20, default=KPIDefinition.SCHEMA_VERSION)
    kpi_definitions_snapshot = models.JSONField(default=dict)
    kpi_data = models.JSONField(default=dict)
    usage_data = models.JSONField(default=dict)
    csat_data = models.JSONField(default=dict)
    notes = models.TextField(blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_pilot_report"
        ordering = ["-generated_at"]

    def __str__(self):
        return f"{self.title} ({self.report_type})"


class DataQualityLog(models.Model):
    source = models.CharField(max_length=100)
    total_records = models.PositiveIntegerField()
    missing_values = models.PositiveIntegerField(default=0)
    outliers_detected = models.PositiveIntegerField(default=0)
    records_cleaned = models.PositiveIntegerField(default=0)
    quality_score = models.FloatField(default=0)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_data_quality_log"
        ordering = ["-created_at"]


class ETLRun(models.Model):
    class RunStatus(models.TextChoices):
        RUNNING = "running", "Đang chạy"
        SUCCESS = "success", "Thành công"
        FAILED = "failed", "Thất bại"
        ROLLED_BACK = "rolled_back", "Đã rollback"

    run_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    input_file = models.CharField(max_length=500)
    semester = models.CharField(max_length=20)
    input_checksum = models.CharField(max_length=64)
    output_checksum = models.CharField(max_length=64, blank=True)
    schema_snapshot = models.JSONField(default=dict)
    input_version = models.CharField(max_length=50)
    output_version = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=RunStatus.choices, default=RunStatus.RUNNING)
    total_records = models.PositiveIntegerField(default=0)
    records_imported = models.PositiveIntegerField(default=0)
    records_skipped = models.PositiveIntegerField(default=0)
    missing_values_handled = models.PositiveIntegerField(default=0)
    outliers_flagged = models.PositiveIntegerField(default=0)
    duplicates_found = models.PositiveIntegerField(default=0)
    columns_excluded = models.JSONField(default=list)
    outlier_review_queue = models.JSONField(default=list)
    error_message = models.TextField(blank=True)
    report = models.JSONField(default=dict)
    parameters = models.JSONField(default=dict)
    random_seed = models.IntegerField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "palp_etl_run"
        ordering = ["-started_at"]

    def __str__(self):
        return f"ETL {self.run_id} [{self.status}]"
