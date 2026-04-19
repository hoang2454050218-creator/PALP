from django.contrib import admin

from .models import CanonicalSession, DeviceFingerprint, SessionLink


@admin.register(DeviceFingerprint)
class DeviceFingerprintAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "device_hash_short",
        "salt_month",
        "user_agent_family",
        "consent_given",
        "first_seen_at",
        "last_seen_at",
    )
    list_filter = ("consent_given", "salt_month")
    search_fields = ("user__username",)
    readonly_fields = ("first_seen_at", "last_seen_at", "device_hash", "salt_month")

    def device_hash_short(self, obj):
        return f"{obj.device_hash[:12]}…"

    device_hash_short.short_description = "Device hash"


@admin.register(CanonicalSession)
class CanonicalSessionAdmin(admin.ModelAdmin):
    list_display = ("canonical_id", "user", "started_at", "last_event_at")
    search_fields = ("user__username", "canonical_id")
    readonly_fields = ("canonical_id", "started_at", "last_event_at")
    date_hierarchy = "started_at"


@admin.register(SessionLink)
class SessionLinkAdmin(admin.ModelAdmin):
    list_display = ("raw_session_id", "canonical_session", "fingerprint", "created_at")
    search_fields = ("raw_session_id", "canonical_session__canonical_id")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
