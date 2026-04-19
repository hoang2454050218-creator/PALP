from django.contrib import admin

from emergency.models import (
    CounselorQueueEntry,
    EmergencyContact,
    EmergencyEvent,
)


@admin.register(EmergencyEvent)
class EmergencyEventAdmin(admin.ModelAdmin):
    list_display = (
        "id", "student", "severity", "status",
        "detector_score", "detected_at", "sla_target_at",
        "acknowledged_at", "resolved_at",
    )
    list_filter = ("severity", "status")
    raw_id_fields = ("student", "triggering_turn", "acknowledged_by")


@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = ("student", "name", "relationship", "phone", "consent_given")
    list_filter = ("relationship", "consent_given")
    raw_id_fields = ("student",)


@admin.register(CounselorQueueEntry)
class CounselorQueueEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "event", "counselor", "state", "queued_at", "decided_at")
    list_filter = ("state",)
    raw_id_fields = ("event", "counselor")
