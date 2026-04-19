from django.contrib import admin

from privacy_dp.models import DPQueryLog, EpsilonBudget


@admin.register(EpsilonBudget)
class EpsilonBudgetAdmin(admin.ModelAdmin):
    list_display = (
        "scope", "period_start", "period_end",
        "epsilon_total", "epsilon_spent", "remaining_display",
    )
    list_filter = ("scope",)
    search_fields = ("scope", "description")

    def remaining_display(self, obj):
        return f"{obj.remaining:.4f}"
    remaining_display.short_description = "Remaining ε"


@admin.register(DPQueryLog)
class DPQueryLogAdmin(admin.ModelAdmin):
    list_display = (
        "id", "budget", "actor", "mechanism", "query_kind",
        "epsilon_spent", "sensitivity", "raw_value", "noisy_value",
        "created_at",
    )
    list_filter = ("mechanism", "query_kind")
    raw_id_fields = ("budget", "actor")
