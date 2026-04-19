from django.contrib import admin

from .models import BehaviorScore, SignalSession


@admin.register(SignalSession)
class SignalSessionAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "window_start",
        "focus_minutes",
        "idle_minutes",
        "tab_switches",
        "frustration_score",
        "give_up_count",
        "raw_event_count",
    )
    list_filter = ("window_start",)
    search_fields = ("student__username", "raw_session_id")
    readonly_fields = ("created_at", "updated_at", "session_quality")
    date_hierarchy = "window_start"


@admin.register(BehaviorScore)
class BehaviorScoreAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "day",
        "total_focus_minutes",
        "avg_focus_score",
        "avg_frustration_score",
        "total_give_up_count",
        "sessions_count",
    )
    search_fields = ("student__username",)
    readonly_fields = ("computed_at",)
    date_hierarchy = "day"
