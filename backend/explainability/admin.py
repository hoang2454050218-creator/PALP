from django.contrib import admin

from explainability.models import (
    CounterfactualScenario,
    ExplanationRecord,
    FeatureContribution,
)


@admin.register(ExplanationRecord)
class ExplanationRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "kind", "method", "summary", "created_at")
    list_filter = ("kind", "method")
    raw_id_fields = ("subject",)


@admin.register(FeatureContribution)
class FeatureContributionAdmin(admin.ModelAdmin):
    list_display = ("id", "explanation", "feature_key", "contribution", "rank")
    list_filter = ("feature_key",)
    raw_id_fields = ("explanation",)


@admin.register(CounterfactualScenario)
class CounterfactualScenarioAdmin(admin.ModelAdmin):
    list_display = (
        "id", "explanation", "feature_key",
        "current_value", "target_value", "expected_delta", "feasibility",
    )
    raw_id_fields = ("explanation",)
