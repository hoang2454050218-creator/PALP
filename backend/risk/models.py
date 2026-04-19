"""
Persisted RiskScore history.

The composite is recomputed on demand by ``risk.scoring.compute_risk_score``
and snapshotted into ``RiskScore`` rows so:

* the lecturer dashboard can chart the trend without rerunning the full
  computation each time.
* the dashboard ``compute_early_warnings`` consumer can join on the
  latest snapshot rather than triggering an inline recompute (keeping the
  early-warning Celery cheap).
* the survival model (Phase 5D) has labelled time-varying covariates.
"""
from django.conf import settings
from django.db import models


class RiskScore(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="risk_scores",
    )
    course = models.ForeignKey(
        "curriculum.Course",
        on_delete=models.CASCADE,
        related_name="risk_scores",
        null=True,
        blank=True,
        help_text="Optional — null means the score is course-agnostic.",
    )
    composite = models.FloatField(
        help_text="0-100 composite. 0 = no risk, 100 = highest risk.",
    )
    dimensions = models.JSONField(
        default=dict,
        help_text="{academic, behavioral, engagement, psychological, metacognitive} -> 0..1",
    )
    components = models.JSONField(
        default=dict,
        help_text="Per-component sub-scores in 0..1 with the input data point used.",
    )
    explanation = models.JSONField(
        default=list,
        help_text="Top-N drivers as [{name, contribution_pct, hint}] for the XAI panel.",
    )
    weights_used = models.JSONField(
        default=dict,
        help_text="Snapshot of PALP_RISK_WEIGHTS at compute time (audit).",
    )
    sample_window_days = models.PositiveSmallIntegerField(default=14)
    computed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "palp_risk_score"
        ordering = ["-computed_at"]
        indexes = [
            models.Index(fields=["student", "-computed_at"]),
            models.Index(fields=["course", "-computed_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.student_id}@{self.computed_at:%Y-%m-%d %H:%M}: {self.composite:.1f}"

    @property
    def severity(self) -> str:
        from django.conf import settings as _s
        thresholds = _s.PALP_RISK_THRESHOLDS
        if self.composite >= thresholds["ALERT_RED"]:
            return "red"
        if self.composite >= thresholds["ALERT_YELLOW"]:
            return "yellow"
        return "green"
