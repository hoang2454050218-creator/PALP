"""Serializers for the Peer Engine HTTP layer.

We deliberately do not expose internal cohort labels, ranks, names, or
absolute mastery scores of other students through any of these
serializers — only aggregate / opaque values. The student fields on
``ReciprocalPeerMatch`` are exposed through a thin display serializer
that strips emails / IDs the requesting student doesn't need.
"""
from __future__ import annotations

from rest_framework import serializers

from peer.models import (
    HerdCluster,
    PeerConsent,
    ReciprocalPeerMatch,
    TeachingSession,
)


class PeerConsentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeerConsent
        fields = [
            "frontier_mode",
            "peer_comparison",
            "peer_teaching",
            "prompt_shown_at",
            "updated_at",
        ]
        read_only_fields = ["prompt_shown_at", "updated_at"]


class _PartnerDisplaySerializer(serializers.Serializer):
    """Intentionally minimal — first name + last initial only."""

    id = serializers.IntegerField()
    display_name = serializers.SerializerMethodField()

    def get_display_name(self, user) -> str:
        first = (getattr(user, "first_name", "") or "").strip()
        last = (getattr(user, "last_name", "") or "").strip()
        if not first and not last:
            return user.username
        if last:
            return f"{first} {last[:1].upper()}."
        return first


class _ConceptDisplaySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    code = serializers.CharField()


class ReciprocalPeerMatchSerializer(serializers.ModelSerializer):
    partner = serializers.SerializerMethodField()
    you_teach = serializers.SerializerMethodField()
    you_learn = serializers.SerializerMethodField()

    class Meta:
        model = ReciprocalPeerMatch
        fields = [
            "id",
            "status",
            "compatibility_score",
            "partner",
            "you_teach",
            "you_learn",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def _viewer(self):
        request = self.context.get("request")
        return getattr(request, "user", None)

    def _is_a(self, obj) -> bool:
        viewer = self._viewer()
        return viewer is not None and obj.student_a_id == viewer.id

    def get_partner(self, obj):
        partner = obj.student_b if self._is_a(obj) else obj.student_a
        return _PartnerDisplaySerializer(partner).data

    def get_you_teach(self, obj):
        concept = obj.concept_a_to_b if self._is_a(obj) else obj.concept_b_to_a
        return _ConceptDisplaySerializer(concept).data

    def get_you_learn(self, obj):
        concept = obj.concept_b_to_a if self._is_a(obj) else obj.concept_a_to_b
        return _ConceptDisplaySerializer(concept).data


class TeachingSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeachingSession
        fields = [
            "id",
            "match",
            "started_at",
            "ended_at",
            "current_round",
            "a_rating_by_b",
            "b_rating_by_a",
            "a_mastery_delta_after",
            "b_mastery_delta_after",
            "notes",
        ]
        read_only_fields = [
            "started_at",
            "a_mastery_delta_after",
            "b_mastery_delta_after",
        ]


class HerdClusterSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source="student_class.name", read_only=True)
    fairness_passed = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()

    class Meta:
        model = HerdCluster
        fields = [
            "id",
            "class_name",
            "detected_at",
            "severity",
            "mean_risk_score",
            "behaviour_summary",
            "fairness_passed",
            "flagged_for_review",
            "is_resolved",
            "resolved_at",
            "reviewer_notes",
            "members",
        ]
        read_only_fields = fields

    def get_fairness_passed(self, obj) -> bool:
        return bool(obj.fairness_audit and obj.fairness_audit.passed)

    def get_members(self, obj) -> list[dict]:
        # PII-light; lecturer needs to see who the members are to
        # decide on intervention so we expose username + display name
        # but never a percentile/rank.
        return [
            {
                "id": m.id,
                "username": m.username,
                "display_name": _display(m),
            }
            for m in obj.members.all()
        ]


def _display(user) -> str:
    first = (getattr(user, "first_name", "") or "").strip()
    last = (getattr(user, "last_name", "") or "").strip()
    if not first and not last:
        return user.username
    return f"{first} {last}".strip()
