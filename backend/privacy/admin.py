from django.contrib import admin
from .models import AuditLog, ConsentRecord, DataDeletionRequest, PrivacyIncident


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "purpose", "granted", "version", "created_at")
    list_filter = ("purpose", "granted", "version")
    search_fields = ("user__username",)
    readonly_fields = (
        "user", "purpose", "granted", "version",
        "ip_address", "user_agent", "created_at",
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("actor", "action", "target_user", "resource", "created_at")
    list_filter = ("action",)
    search_fields = ("actor__username", "target_user__username", "resource")
    readonly_fields = (
        "actor", "action", "target_user", "resource",
        "detail", "ip_address", "request_id", "created_at",
    )


@admin.register(PrivacyIncident)
class PrivacyIncidentAdmin(admin.ModelAdmin):
    list_display = ("title", "severity", "status", "is_within_sla", "created_at")
    list_filter = ("severity", "status")
    search_fields = ("title", "description")


@admin.register(DataDeletionRequest)
class DataDeletionRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "tiers", "status", "requested_at", "completed_at")
    list_filter = ("status",)
    readonly_fields = (
        "user", "tiers", "status", "result_summary",
        "requested_at", "completed_at",
    )
