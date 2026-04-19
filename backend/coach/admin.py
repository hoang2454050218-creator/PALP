from django.contrib import admin

from coach.models import (
    CoachAuditLog,
    CoachConsent,
    CoachConversation,
    CoachTurn,
)


@admin.register(CoachConsent)
class CoachConsentAdmin(admin.ModelAdmin):
    list_display = (
        "student", "ai_coach_local", "ai_coach_cloud",
        "share_emergency_contact", "cooldown_until", "updated_at",
    )
    list_filter = ("ai_coach_local", "ai_coach_cloud")
    search_fields = ("student__username", "student__email")


@admin.register(CoachConversation)
class CoachConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "status", "turn_count", "started_at", "ended_at")
    list_filter = ("status",)
    raw_id_fields = ("student",)


@admin.register(CoachTurn)
class CoachTurnAdmin(admin.ModelAdmin):
    list_display = (
        "id", "conversation", "turn_number", "role",
        "intent", "llm_provider", "refusal_triggered",
        "emergency_triggered", "created_at",
    )
    list_filter = ("role", "refusal_triggered", "emergency_triggered", "llm_provider")
    raw_id_fields = ("conversation",)


@admin.register(CoachAuditLog)
class CoachAuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "id", "turn", "intent", "llm_provider", "tokens_in", "tokens_out",
        "latency_ms", "refusal_triggered", "emergency_triggered", "created_at",
    )
    list_filter = ("llm_provider", "refusal_triggered", "emergency_triggered")
    raw_id_fields = ("turn",)
