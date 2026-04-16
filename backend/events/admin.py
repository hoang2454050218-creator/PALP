from django.contrib import admin
from .models import EventLog


@admin.register(EventLog)
class EventLogAdmin(admin.ModelAdmin):
    list_display = (
        "event_name",
        "actor_type",
        "actor",
        "session_id",
        "course",
        "device_type",
        "timestamp_utc",
        "confirmed_at",
    )
    list_filter = ("event_name", "actor_type", "device_type")
    search_fields = ("session_id", "source_page", "actor__username")
    readonly_fields = (
        "event_name",
        "event_version",
        "timestamp_utc",
        "client_timestamp",
        "actor_type",
        "actor",
        "session_id",
        "course",
        "student_class",
        "device_type",
        "source_page",
        "request_id",
        "idempotency_key",
        "concept",
        "task",
        "difficulty_level",
        "attempt_number",
        "mastery_before",
        "mastery_after",
        "intervention_reason",
        "confirmed_at",
        "properties",
    )
    date_hierarchy = "timestamp_utc"
