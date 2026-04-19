"""Django admin registrations for the Peer Engine."""
from django.contrib import admin

from peer.models import (
    HerdCluster,
    PeerCohort,
    PeerConsent,
    ReciprocalPeerMatch,
    TeachingSession,
)


@admin.register(PeerConsent)
class PeerConsentAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "frontier_mode",
        "peer_comparison",
        "peer_teaching",
        "prompt_shown_at",
        "updated_at",
    )
    list_filter = ("peer_comparison", "peer_teaching", "frontier_mode")
    search_fields = ("student__username", "student__email")


@admin.register(PeerCohort)
class PeerCohortAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "student_class",
        "ability_band_label",
        "members_count",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "student_class")
    search_fields = ("ability_band_label", "student_class__name")
    raw_id_fields = ("student_class", "fairness_audit")
    filter_horizontal = ("members",)


@admin.register(ReciprocalPeerMatch)
class ReciprocalPeerMatchAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "student_a",
        "student_b",
        "concept_a_to_b",
        "concept_b_to_a",
        "compatibility_score",
        "status",
        "created_at",
    )
    list_filter = ("status",)
    raw_id_fields = (
        "cohort", "student_a", "student_b",
        "concept_a_to_b", "concept_b_to_a",
    )


@admin.register(TeachingSession)
class TeachingSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "match",
        "current_round",
        "started_at",
        "ended_at",
        "a_rating_by_b",
        "b_rating_by_a",
    )
    list_filter = ("current_round",)
    raw_id_fields = ("match",)


@admin.register(HerdCluster)
class HerdClusterAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "student_class",
        "severity",
        "mean_risk_score",
        "flagged_for_review",
        "is_resolved",
        "detected_at",
    )
    list_filter = ("severity", "is_resolved", "flagged_for_review")
    raw_id_fields = ("student_class", "fairness_audit", "reviewed_by")
    filter_horizontal = ("members",)
    readonly_fields = ("detected_at",)
