from django.contrib import admin
from .models import (
    DataQualityLog,
    KPIDefinition,
    KPILineageLog,
    KPIVersion,
    PilotReport,
)


class KPIVersionInline(admin.TabularInline):
    model = KPIVersion
    extra = 0
    readonly_fields = (
        "version", "definition_snapshot", "change_reason",
        "created_by", "created_at",
    )
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(KPIDefinition)
class KPIDefinitionAdmin(admin.ModelAdmin):
    list_display = (
        "code", "name", "owner", "target_value",
        "target_direction", "is_locked", "current_version",
    )
    list_filter = ("is_locked", "target_direction")
    search_fields = ("code", "name")
    inlines = [KPIVersionInline]
    readonly_fields = ("current_version", "created_at", "updated_at")

    def get_readonly_fields(self, request, obj=None):
        base = list(super().get_readonly_fields(request, obj))
        if obj and obj.is_locked:
            base += list(KPIDefinition.LOCKED_FIELDS)
        return base


@admin.register(KPILineageLog)
class KPILineageLogAdmin(admin.ModelAdmin):
    list_display = (
        "kpi", "week_number", "class_id", "computed_value",
        "event_count", "definition_version", "computed_at",
    )
    list_filter = ("kpi__code", "week_number")
    readonly_fields = (
        "kpi", "report", "week_number", "class_id", "computed_value",
        "event_count", "event_date_range", "sample_event_ids",
        "computation_params", "data_quality_flags",
        "definition_version", "computed_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(PilotReport)
class PilotReportAdmin(admin.ModelAdmin):
    list_display = (
        "title", "report_type", "week_number",
        "schema_version", "generated_at",
    )
    list_filter = ("report_type", "schema_version")
    readonly_fields = ("schema_version", "kpi_definitions_snapshot")


@admin.register(DataQualityLog)
class DataQualityLogAdmin(admin.ModelAdmin):
    list_display = ("source", "total_records", "quality_score", "created_at")
    list_filter = ("source",)
