from django.contrib import admin
from .models import WellbeingNudge


@admin.register(WellbeingNudge)
class WellbeingNudgeAdmin(admin.ModelAdmin):
    list_display = ("student", "nudge_type", "response", "continuous_minutes", "created_at")
    list_filter = ("nudge_type", "response")
