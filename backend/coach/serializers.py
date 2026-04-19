"""Serializers for the Coach HTTP layer."""
from __future__ import annotations

from rest_framework import serializers

from coach.models import (
    CoachAuditLog,
    CoachConsent,
    CoachConversation,
    CoachTurn,
)


class CoachConsentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoachConsent
        fields = [
            "ai_coach_local",
            "ai_coach_cloud",
            "share_emergency_contact",
            "cooldown_until",
            "updated_at",
        ]
        read_only_fields = ["cooldown_until", "updated_at"]


class CoachTurnSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoachTurn
        fields = [
            "id",
            "turn_number",
            "role",
            "content",
            "intent",
            "llm_provider",
            "llm_model",
            "refusal_triggered",
            "emergency_triggered",
            "created_at",
        ]
        read_only_fields = fields


class CoachConversationSerializer(serializers.ModelSerializer):
    turns = CoachTurnSerializer(many=True, read_only=True)

    class Meta:
        model = CoachConversation
        fields = [
            "id",
            "status",
            "started_at",
            "ended_at",
            "turn_count",
            "last_intent",
            "turns",
        ]
        read_only_fields = fields


class CoachConversationListSerializer(serializers.ModelSerializer):
    """Compact list view — no turns to keep the payload small."""

    class Meta:
        model = CoachConversation
        fields = [
            "id",
            "status",
            "started_at",
            "ended_at",
            "turn_count",
            "last_intent",
        ]
        read_only_fields = fields
