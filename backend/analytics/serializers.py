from rest_framework import serializers
from .models import (
    DataQualityLog,
    KPIDefinition,
    KPILineageLog,
    KPIVersion,
    PilotReport,
)


class PilotReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = PilotReport
        fields = (
            "id", "title", "report_type", "week_number", "schema_version",
            "kpi_definitions_snapshot", "kpi_data", "usage_data",
            "csat_data", "notes", "generated_at",
        )


class DataQualityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataQualityLog
        fields = (
            "id", "source", "total_records", "missing_values",
            "outliers_detected", "records_cleaned", "quality_score",
            "details", "created_at",
        )


class KPISnapshotSerializer(serializers.Serializer):
    week = serializers.IntegerField()
    cohort_size = serializers.IntegerField()
    active_learning_minutes_per_week = serializers.FloatField()
    micro_task_completion_rate = serializers.FloatField()
    dashboard_usage_per_week = serializers.IntegerField()
    mastery = serializers.DictField()
    alerts = serializers.DictField()
    wellbeing = serializers.DictField()
    integrity = serializers.DictField(required=False)


class KPIVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = KPIVersion
        fields = (
            "id", "version", "definition_snapshot",
            "change_reason", "created_at",
        )


class KPILineageSerializer(serializers.ModelSerializer):
    kpi_code = serializers.CharField(source="kpi.code", read_only=True)

    class Meta:
        model = KPILineageLog
        fields = (
            "id", "kpi_code", "week_number", "class_id",
            "computed_value", "event_count", "event_date_range",
            "sample_event_ids", "computation_params",
            "data_quality_flags", "definition_version", "computed_at",
        )


class KPIDefinitionSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    versions = KPIVersionSerializer(many=True, read_only=True)
    latest_lineage = serializers.SerializerMethodField()
    integrity_status = serializers.SerializerMethodField()

    class Meta:
        model = KPIDefinition
        fields = (
            "id", "code", "name", "owner", "owner_username",
            "description", "unit", "target_value", "target_direction",
            "source_events", "query_function", "query_sql",
            "baseline_value", "baseline_locked_at",
            "baseline_period_start", "baseline_period_end",
            "intervention_period_start", "intervention_period_end",
            "is_locked", "current_version",
            "created_at", "updated_at",
            "versions", "latest_lineage", "integrity_status",
        )

    def get_latest_lineage(self, obj):
        entry = obj.lineage_logs.first()
        if entry is None:
            return None
        return KPILineageSerializer(entry).data

    def get_integrity_status(self, obj):
        latest_audit = DataQualityLog.objects.filter(
            source="kpi_integrity_audit",
        ).order_by("-created_at").first()
        if latest_audit is None:
            return {"status": "no_audit_yet"}
        details = latest_audit.details or {}
        return details.get(obj.code, {"status": "not_found_in_audit"})
