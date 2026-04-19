from django.contrib import admin

from .models import RiskScore


@admin.register(RiskScore)
class RiskScoreAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "composite", "severity", "sample_window_days", "computed_at")
    list_filter = ("course",)
    search_fields = ("student__username",)
    readonly_fields = (
        "composite",
        "dimensions",
        "components",
        "explanation",
        "weights_used",
        "sample_window_days",
        "computed_at",
        "severity",
    )
    date_hierarchy = "computed_at"
