from django.contrib import admin
from .models import Alert, InterventionAction


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("student", "severity", "status", "trigger_type", "created_at")
    list_filter = ("severity", "status", "trigger_type")


@admin.register(InterventionAction)
class InterventionActionAdmin(admin.ModelAdmin):
    list_display = ("lecturer", "action_type", "follow_up_status", "created_at")
    list_filter = ("action_type", "follow_up_status")
