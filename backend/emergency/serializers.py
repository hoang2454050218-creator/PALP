"""Serializers for Emergency Pipeline."""
from __future__ import annotations

from rest_framework import serializers

from emergency.models import (
    CounselorQueueEntry,
    EmergencyContact,
    EmergencyEvent,
)


class _StudentDisplay(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    display_name = serializers.SerializerMethodField()

    def get_display_name(self, user) -> str:
        first = (getattr(user, "first_name", "") or "").strip()
        last = (getattr(user, "last_name", "") or "").strip()
        full = f"{first} {last}".strip()
        return full or user.username


class EmergencyEventSerializer(serializers.ModelSerializer):
    student = _StudentDisplay(read_only=True)

    class Meta:
        model = EmergencyEvent
        fields = [
            "id",
            "student",
            "severity",
            "status",
            "detected_keywords",
            "detector_score",
            "detected_at",
            "sla_target_at",
            "acknowledged_at",
            "acknowledged_by",
            "resolved_at",
            "resolution_notes",
            "follow_up_24h_at",
            "follow_up_48h_at",
            "follow_up_72h_at",
            "contacted_emergency_contact",
        ]
        read_only_fields = fields


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = [
            "id",
            "name",
            "phone",
            "email",
            "relationship",
            "consent_given",
            "consent_given_at",
            "updated_at",
        ]
        read_only_fields = ["id", "consent_given_at", "updated_at"]


class CounselorQueueEntrySerializer(serializers.ModelSerializer):
    event = EmergencyEventSerializer(read_only=True)

    class Meta:
        model = CounselorQueueEntry
        fields = [
            "id",
            "event",
            "state",
            "queued_at",
            "viewed_at",
            "decided_at",
        ]
        read_only_fields = fields
