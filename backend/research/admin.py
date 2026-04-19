from __future__ import annotations

from django.contrib import admin

from .models import AnonymizedExport, ResearchParticipation, ResearchProtocol


@admin.register(ResearchProtocol)
class ResearchProtocolAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "status", "irb_number", "retention_months", "updated_at")
    list_filter = ("status",)
    search_fields = ("code", "title", "pi_name", "pi_email", "irb_number")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ResearchParticipation)
class ResearchParticipationAdmin(admin.ModelAdmin):
    list_display = ("student", "protocol", "state", "decided_at", "withdrawn_at")
    list_filter = ("state", "protocol")
    search_fields = ("student__username", "student__email", "protocol__code")
    readonly_fields = ("decided_at", "withdrawn_at", "consent_text_version")


@admin.register(AnonymizedExport)
class AnonymizedExportAdmin(admin.ModelAdmin):
    list_display = (
        "id", "protocol", "dataset_key", "record_count",
        "k_anonymity_value", "k_anonymity_passed", "created_at",
    )
    list_filter = ("k_anonymity_passed", "protocol")
    search_fields = ("dataset_key", "protocol__code")
    readonly_fields = (
        "created_at", "record_count", "participant_count",
        "k_anonymity_value", "k_anonymity_passed",
        "suppressed_columns", "salt_id",
    )
