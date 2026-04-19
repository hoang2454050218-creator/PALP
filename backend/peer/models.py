"""Peer Engine models — Phase 3 of v3 MAXIMAL roadmap.

Implements the four mechanisms described in
``docs/PEER_ENGINE_DESIGN.md``:

* **PeerConsent** — per-feature opt-in flags. ``frontier_mode`` defaults
  ON because it never compares to anyone else; ``peer_comparison`` and
  ``peer_teaching`` default OFF and stay off until the student gives
  explicit consent (after the four-week onboarding window).
* **PeerCohort** — k-means cluster of same-ability students for safe
  benchmarking. Re-clustered weekly. Minimum size 10 enforced at the
  service layer.
* **ReciprocalPeerMatch** — A(strong X, weak Y) ↔ B(weak X, strong Y).
  Both directions required so the match supports the protégé effect
  rather than one-way tutoring.
* **TeachingSession** — turn-based session tied to a match. Mutual
  ratings + per-side mastery delta close the loop for the
  causal/uplift evaluator in Phase 0.
* **HerdCluster** — DBSCAN on 14-day behaviour vectors. Always paired
  with a fairness audit before any lecturer-side intervention is
  surfaced. ``flagged_for_review`` blocks intervention copy when audit
  fails.

All models are additive — none replace anything in adaptive/, signals/
or risk/. They reference existing FK targets (``accounts.User``,
``accounts.StudentClass``, ``curriculum.Concept``) so nothing in the
existing schema has to change.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models


class PeerConsent(models.Model):
    """Per-student opt-in flags for the four peer mechanisms.

    Created lazily on first peer-page visit (or by the onboarding
    job). The defaults match the anti-herd philosophy: only frontier
    mode is on. Anything that compares the student to other students
    requires an explicit toggle.
    """

    student = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="peer_consent",
    )

    frontier_mode = models.BooleanField(
        default=True,
        help_text="Past-self vs current-self comparison. No peer data involved.",
    )
    peer_comparison = models.BooleanField(
        default=False,
        help_text="Anonymous percentile band within the same-ability cohort.",
    )
    peer_teaching = models.BooleanField(
        default=False,
        help_text="Eligible for reciprocal teaching matches and sessions.",
    )

    prompt_shown_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Last time the 4-week opt-in prompt was surfaced to the student.",
    )
    last_revoked_purpose = models.CharField(max_length=40, blank=True)
    last_revoked_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_peer_consent"

    def __str__(self) -> str:
        return f"PeerConsent({self.student.username})"


class PeerCohort(models.Model):
    """A cluster of same-ability students within a class.

    Built weekly by ``services.cohort_builder.build_cohorts``. Minimum
    size 10 enforced at construction time so percentile bands cannot
    be reverse-engineered to a single student. ``ability_band_label``
    is opaque ("band_0", "band_1", …) — never displayed to students,
    used only by lecturers in admin to sanity-check the clustering.
    """

    student_class = models.ForeignKey(
        "accounts.StudentClass",
        on_delete=models.CASCADE,
        related_name="peer_cohorts",
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="peer_cohorts",
        blank=True,
    )

    ability_band_label = models.CharField(max_length=32)
    members_count = models.PositiveIntegerField(default=0)

    centroid = models.JSONField(
        default=list, blank=True,
        help_text="K-means centroid vector in concept-mastery space.",
    )
    fairness_audit = models.ForeignKey(
        "fairness.FairnessAudit",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="peer_cohorts",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_peer_cohort"
        indexes = [
            models.Index(fields=["student_class", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.student_class.name}/{self.ability_band_label} (n={self.members_count})"


class ReciprocalPeerMatch(models.Model):
    """Pair of students linked for reciprocal teaching.

    Stores the *concept axes* of the match — A teaches
    ``concept_a_to_b`` to B, B teaches ``concept_b_to_a`` to A. Both
    must be set; matches with only one direction are rejected by the
    matcher because they regress to one-way tutoring (less effective
    per Topping 2005).
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Đang chờ đồng ý"
        ACTIVE = "active", "Đang hoạt động"
        ARCHIVED = "archived", "Đã lưu trữ"
        DECLINED = "declined", "Đã từ chối"

    cohort = models.ForeignKey(
        PeerCohort, on_delete=models.CASCADE, related_name="matches",
        null=True, blank=True,
    )
    student_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="peer_matches_as_a",
    )
    student_b = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="peer_matches_as_b",
    )
    concept_a_to_b = models.ForeignKey(
        "curriculum.Concept",
        on_delete=models.PROTECT,
        related_name="matches_as_taught_a_to_b",
    )
    concept_b_to_a = models.ForeignKey(
        "curriculum.Concept",
        on_delete=models.PROTECT,
        related_name="matches_as_taught_b_to_a",
    )
    compatibility_score = models.FloatField(
        default=0.0,
        help_text="Composite score; higher = stronger reciprocity.",
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_peer_match"
        indexes = [
            models.Index(fields=["student_a", "status"]),
            models.Index(fields=["student_b", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(student_a=models.F("student_b")),
                name="peer_match_distinct_students",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student_a_id}↔{self.student_b_id} [{self.status}]"


class TeachingSession(models.Model):
    """A single 60-minute reciprocal teaching session.

    Tracks the round the pair is in plus mutual ratings and per-side
    mastery delta. Mastery delta is computed offline once both
    students have submitted at least one task on the concept they
    were taught — see ``services.session_evaluator``.
    """

    class Round(models.TextChoices):
        BRIEF = "brief", "Giới thiệu"
        A_TEACHES_X = "a_teaches_x", "A dạy X cho B"
        B_ASKS = "b_asks", "B hỏi rõ"
        B_TEACHES_Y = "b_teaches_y", "B dạy Y cho A"
        A_ASKS = "a_asks", "A hỏi rõ"
        MUTUAL_RATING = "mutual_rating", "Đánh giá lẫn nhau"
        FOLLOW_UP = "follow_up", "Bài tập theo dõi"
        COMPLETED = "completed", "Hoàn thành"

    match = models.ForeignKey(
        ReciprocalPeerMatch,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    current_round = models.CharField(
        max_length=20, choices=Round.choices, default=Round.BRIEF,
    )

    a_rating_by_b = models.PositiveSmallIntegerField(null=True, blank=True)
    b_rating_by_a = models.PositiveSmallIntegerField(null=True, blank=True)
    a_mastery_delta_after = models.FloatField(null=True, blank=True)
    b_mastery_delta_after = models.FloatField(null=True, blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        db_table = "palp_peer_teaching_session"
        indexes = [
            models.Index(fields=["match", "-started_at"]),
        ]

    def __str__(self) -> str:
        return f"Session({self.match_id}) round={self.current_round}"


class HerdCluster(models.Model):
    """A behaviour cluster flagged as potentially negative-influence.

    Stored only when the cluster (a) has mean composite risk above
    threshold and (b) has at least ``HERD_MIN_SAMPLES`` members.
    The fairness audit always runs and the *result* is referenced —
    if it fails, ``flagged_for_review = True`` and the lecturer-side
    intervention copy is suppressed until a human reviews it.
    """

    class Severity(models.TextChoices):
        MEDIUM = "medium", "Trung bình"
        HIGH = "high", "Cao"
        CRITICAL = "critical", "Nghiêm trọng"

    student_class = models.ForeignKey(
        "accounts.StudentClass",
        on_delete=models.CASCADE,
        related_name="herd_clusters",
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="herd_clusters",
        blank=True,
    )

    detected_at = models.DateTimeField(auto_now_add=True)
    severity = models.CharField(
        max_length=16, choices=Severity.choices, default=Severity.MEDIUM,
    )
    mean_risk_score = models.FloatField(default=0.0)

    behaviour_summary = models.JSONField(
        default=dict, blank=True,
        help_text=(
            "Mean focus minutes, missed milestones, give-up count, dismissed "
            "nudges, weekly login days for the cluster (14-day window)."
        ),
    )
    fairness_audit = models.ForeignKey(
        "fairness.FairnessAudit",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="herd_clusters",
    )
    flagged_for_review = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="reviewed_herd_clusters",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewer_notes = models.TextField(blank=True)

    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "palp_peer_herd_cluster"
        indexes = [
            models.Index(fields=["student_class", "-detected_at"]),
            models.Index(fields=["is_resolved", "severity"]),
        ]

    def __str__(self) -> str:
        return (
            f"HerdCluster({self.student_class.name}) "
            f"sev={self.severity} risk={self.mean_risk_score:.0f}"
        )
