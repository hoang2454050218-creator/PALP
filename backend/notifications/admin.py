from django.contrib import admin

from notifications.models import Notification, NotificationPreference


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        "user", "in_app_enabled", "email_enabled", "push_enabled",
        "quiet_hours_start", "quiet_hours_end",
    )
    list_filter = ("in_app_enabled", "email_enabled", "push_enabled")
    raw_id_fields = ("user",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "category", "severity", "channel",
        "title", "created_at", "read_at",
    )
    list_filter = ("category", "severity", "channel")
    raw_id_fields = ("user",)
    search_fields = ("title", "body")
