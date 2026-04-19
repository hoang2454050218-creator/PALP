from django.contrib import admin

from .models import FairnessAudit


@admin.register(FairnessAudit)
class FairnessAuditAdmin(admin.ModelAdmin):
    list_display = ("target_name", "kind", "passed", "sample_size", "reviewed_by", "created_at")
    list_filter = ("kind", "passed")
    search_fields = ("target_name", "notes")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
