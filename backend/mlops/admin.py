from django.contrib import admin

from .models import DriftReport, FeatureView, ModelRegistry, ModelVersion, ShadowComparison


@admin.register(ModelRegistry)
class ModelRegistryAdmin(admin.ModelAdmin):
    list_display = ("name", "model_type", "owner", "created_at", "updated_at")
    list_filter = ("model_type",)
    search_fields = ("name", "description")
    autocomplete_fields = ("owner",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(ModelVersion)
class ModelVersionAdmin(admin.ModelAdmin):
    list_display = (
        "registry",
        "semver",
        "status",
        "fairness_passed",
        "epsilon_dp",
        "promoted_at",
        "created_at",
    )
    list_filter = ("status", "fairness_passed", "registry__model_type")
    search_fields = ("registry__name", "semver", "artifact_uri")
    autocomplete_fields = ("registry", "promoted_by")
    readonly_fields = ("created_at",)
    fieldsets = (
        (None, {"fields": ("registry", "semver", "status")}),
        ("Artifact", {"fields": ("artifact_uri", "training_data_ref", "model_card_path")}),
        ("Quantitative", {"fields": ("metrics_json", "params_json")}),
        ("Governance", {"fields": ("fairness_passed", "epsilon_dp", "promoted_at", "promoted_by")}),
        ("Audit", {"fields": ("created_at",)}),
    )


@admin.register(FeatureView)
class FeatureViewAdmin(admin.ModelAdmin):
    list_display = ("name", "entity", "source_table", "online_store_enabled", "updated_at")
    list_filter = ("entity", "online_store_enabled")
    search_fields = ("name", "source_table", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(DriftReport)
class DriftReportAdmin(admin.ModelAdmin):
    list_display = (
        "model_version",
        "severity",
        "drift_detected",
        "sample_size",
        "window_start",
        "window_end",
        "created_at",
    )
    list_filter = ("severity", "drift_detected")
    search_fields = ("model_version__registry__name",)
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(ShadowComparison)
class ShadowComparisonAdmin(admin.ModelAdmin):
    list_display = (
        "candidate_version",
        "baseline_version",
        "n_predictions",
        "agreement_pct",
        "mean_abs_diff",
        "p95_abs_diff",
        "created_at",
    )
    search_fields = (
        "candidate_version__registry__name",
        "baseline_version__registry__name",
    )
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
