from django.contrib import admin

from coach_memory.models import (
    EpisodicMemory,
    ProceduralMemory,
    SemanticMemory,
)


@admin.register(EpisodicMemory)
class EpisodicMemoryAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "kind", "summary", "salience", "occurred_at")
    list_filter = ("kind",)
    raw_id_fields = ("student",)
    search_fields = ("summary",)


@admin.register(SemanticMemory)
class SemanticMemoryAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "key", "confidence", "source", "updated_at")
    list_filter = ("key", "source")
    raw_id_fields = ("student",)


@admin.register(ProceduralMemory)
class ProceduralMemoryAdmin(admin.ModelAdmin):
    list_display = (
        "id", "student", "strategy_key",
        "successes", "failures", "effectiveness_estimate", "last_applied_at",
    )
    list_filter = ("strategy_key",)
    raw_id_fields = ("student",)
