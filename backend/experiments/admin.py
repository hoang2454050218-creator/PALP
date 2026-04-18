from django.contrib import admin

from .models import Experiment, ExperimentAssignment, ExperimentVariant


class VariantInline(admin.TabularInline):
    model = ExperimentVariant
    extra = 1


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "primary_metric", "metric_kind", "started_at")
    list_filter = ("status", "metric_kind")
    search_fields = ("name", "hypothesis")
    inlines = [VariantInline]


@admin.register(ExperimentAssignment)
class ExperimentAssignmentAdmin(admin.ModelAdmin):
    list_display = ("experiment", "user", "variant", "assigned_at")
    list_filter = ("experiment", "variant")
    search_fields = ("user__username",)
    readonly_fields = ("assigned_at",)
