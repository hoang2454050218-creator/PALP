from django.contrib import admin

from .models import FeatureFlag, FeatureFlagAudit
from .services import invalidate_cache


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = ("name", "enabled", "rollout_pct", "updated_at")
    list_filter = ("enabled",)
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        before = {}
        if change and obj.pk:
            old = FeatureFlag.objects.get(pk=obj.pk)
            before = {
                "enabled": old.enabled,
                "rollout_pct": old.rollout_pct,
                "rules_json": old.rules_json,
            }
        super().save_model(request, obj, form, change)
        FeatureFlagAudit.objects.create(
            flag=obj,
            changed_by=request.user,
            before=before,
            after={
                "enabled": obj.enabled,
                "rollout_pct": obj.rollout_pct,
                "rules_json": obj.rules_json,
            },
        )
        invalidate_cache()


@admin.register(FeatureFlagAudit)
class FeatureFlagAuditAdmin(admin.ModelAdmin):
    list_display = ("flag", "changed_by", "when")
    list_filter = ("flag",)
    readonly_fields = ("flag", "changed_by", "before", "after", "when")
    ordering = ("-when",)
