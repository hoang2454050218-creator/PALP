from django.contrib import admin

from dkt.models import DKTAttemptLog, DKTModelVersion, DKTPrediction


@admin.register(DKTModelVersion)
class DKTModelVersionAdmin(admin.ModelAdmin):
    list_display = ("name", "semver", "family", "status", "created_at", "promoted_at")
    list_filter = ("status", "family")
    search_fields = ("name", "semver")


@admin.register(DKTPrediction)
class DKTPredictionAdmin(admin.ModelAdmin):
    list_display = (
        "id", "student", "concept", "p_correct_next",
        "confidence", "sequence_length", "computed_at",
    )
    list_filter = ("model_version",)
    raw_id_fields = ("student", "concept", "model_version")


@admin.register(DKTAttemptLog)
class DKTAttemptLogAdmin(admin.ModelAdmin):
    list_display = (
        "id", "student", "concept", "is_correct",
        "occurred_at", "hint_count",
    )
    list_filter = ("is_correct",)
    raw_id_fields = ("student", "concept")
