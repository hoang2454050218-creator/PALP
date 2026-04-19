from __future__ import annotations

from django.contrib import admin

from .models import AffectLexiconEntry, AffectSnapshot


@admin.register(AffectSnapshot)
class AffectSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "id", "student", "modality", "label", "valence",
        "arousal", "confidence", "occurred_at",
    )
    list_filter = ("modality", "label")
    search_fields = ("student__username",)
    readonly_fields = ("occurred_at",)


@admin.register(AffectLexiconEntry)
class AffectLexiconAdmin(admin.ModelAdmin):
    list_display = ("term", "polarity", "valence_weight", "arousal_weight", "language")
    list_filter = ("polarity", "language")
    search_fields = ("term",)
    readonly_fields = ("created_at", "updated_at")
