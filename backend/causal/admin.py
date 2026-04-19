from django.contrib import admin

from .models import CausalEvaluation, CausalExperiment


@admin.register(CausalExperiment)
class CausalExperimentAdmin(admin.ModelAdmin):
    list_display = (
        "experiment",
        "primary_outcome_metric",
        "outcome_kind",
        "randomization_unit",
        "is_locked",
        "irb_reference",
        "created_at",
    )
    list_filter = ("outcome_kind", "randomization_unit")
    search_fields = ("experiment__name", "primary_outcome_metric", "irb_reference")
    readonly_fields = ("created_at", "updated_at", "locked_at", "amendments_log")
    autocomplete_fields = ("experiment", "locked_by")
    fieldsets = (
        (None, {"fields": ("experiment", "pre_registration")}),
        ("Outcomes", {"fields": ("primary_outcome_metric", "secondary_outcomes", "outcome_kind")}),
        ("Design", {"fields": ("randomization_unit", "cuped_covariate", "expected_effect_size", "target_sample_per_arm")}),
        ("Compliance", {"fields": ("irb_reference",)}),
        ("Lock", {"fields": ("locked_at", "locked_by", "amendments_log")}),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(CausalEvaluation)
class CausalEvaluationAdmin(admin.ModelAdmin):
    list_display = (
        "experiment",
        "estimator",
        "ate",
        "p_value",
        "n_treatment",
        "n_control",
        "fairness_audit_id",
        "created_at",
    )
    list_filter = ("estimator",)
    search_fields = ("experiment__experiment__name",)
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
