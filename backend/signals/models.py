"""
Rolled-up behavioral signal storage.

Raw events land in ``events.EventLog`` (per-event row). Storing every
focus_lost / tab_switched / idle_started would explode the events table
and make analytics queries slow. Instead, the ingest pipeline pushes raw
events to EventLog **and** updates a per-(student, canonical_session,
5-min-window) ``SignalSession`` rollup row that aggregates the counters
downstream consumers actually care about (RiskScore behavioural
dimension, dashboard signals-health Grafana panel, FSRS cognitive-load
budget, P5 contextual bandit context vector).

``BehaviorScore`` is a daily rollup of ``SignalSession`` for fast
historical queries (per-student trend, per-class signals-health board).
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


def _floor_to_window_start(dt, *, minutes: int = 5):
    """Round a datetime DOWN to the start of the enclosing N-minute window."""
    discard = dt.minute % minutes
    return dt.replace(
        minute=dt.minute - discard,
        second=0,
        microsecond=0,
    )


class SignalSession(models.Model):
    """5-minute behavioural rollup per student per canonical session.

    Updated incrementally by ``signals.services.ingest_events`` so a
    burst of 100 raw events from the frontend produces 1 row mutation
    rather than 100. The ``canonical_session_id`` is sourced from
    ``device_sessions`` so multi-device sessions stitch correctly
    (Phase 0D).
    """

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="signal_sessions",
    )
    canonical_session_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Optional link to device_sessions.CanonicalSession; "
                  "null when sensing fires before stitching is wired.",
    )
    raw_session_id = models.CharField(
        max_length=120,
        blank=True,
        help_text="Frontend-supplied session id; useful for forensics "
                  "before stitching backfills canonical_session_id.",
    )
    window_start = models.DateTimeField(db_index=True)
    window_end = models.DateTimeField()

    # Aggregates (incrementally updated)
    focus_minutes = models.FloatField(default=0.0)
    idle_minutes = models.FloatField(default=0.0)
    tab_switches = models.PositiveIntegerField(default=0)
    hint_count = models.PositiveIntegerField(default=0)
    frustration_score = models.FloatField(
        default=0.0,
        help_text="0-1 composite from frustration_signal events in the window.",
    )
    give_up_count = models.PositiveIntegerField(default=0)
    response_time_outliers = models.PositiveIntegerField(default=0)
    struggle_count = models.PositiveIntegerField(default=0)

    raw_event_count = models.PositiveIntegerField(default=0)
    last_event_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_signal_session"
        ordering = ["-window_start"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "raw_session_id", "window_start"],
                name="uq_signal_session_student_session_window",
            ),
        ]
        indexes = [
            models.Index(fields=["student", "-window_start"]),
            models.Index(fields=["canonical_session_id", "-window_start"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.student_id}@{self.window_start:%Y-%m-%d %H:%M} "
            f"focus={self.focus_minutes:.1f}m frustration={self.frustration_score:.2f}"
        )

    @property
    def session_quality(self) -> float:
        """0-1 composite quality score for the window.

        Used by ``risk.compute_risk_score`` engagement dimension. High when
        focus is high and frustration/give-up are low.
        """
        if self.focus_minutes + self.idle_minutes <= 0:
            return 0.0
        focus_pct = self.focus_minutes / max(0.001, self.focus_minutes + self.idle_minutes)
        return max(
            0.0,
            min(1.0, focus_pct * (1 - self.frustration_score) * (1 - min(1.0, self.give_up_count * 0.2))),
        )


class BehaviorScore(models.Model):
    """Daily rollup of SignalSession per student.

    Computed nightly by ``signals.tasks.rollup_signals_daily``. Used by
    ``risk.scoring`` and lecturer dashboard for historical trends without
    scanning thousands of 5-minute rows per query.
    """

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="behavior_scores",
    )
    day = models.DateField(db_index=True)

    total_focus_minutes = models.FloatField(default=0.0)
    total_idle_minutes = models.FloatField(default=0.0)
    avg_focus_score = models.FloatField(default=0.0)
    avg_frustration_score = models.FloatField(default=0.0)
    total_tab_switches = models.PositiveIntegerField(default=0)
    total_give_up_count = models.PositiveIntegerField(default=0)
    total_struggle_count = models.PositiveIntegerField(default=0)
    total_hint_count = models.PositiveIntegerField(default=0)

    sessions_count = models.PositiveIntegerField(default=0)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_behavior_score"
        ordering = ["-day"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "day"],
                name="uq_behavior_score_student_day",
            ),
        ]
        indexes = [
            models.Index(fields=["student", "-day"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.student_id}@{self.day}: focus={self.total_focus_minutes:.0f}m "
            f"sessions={self.sessions_count}"
        )
