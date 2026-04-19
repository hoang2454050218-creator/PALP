"""
Fairness audit log.

Every classifier or clustering output that affects students must be audited
before release. Results are persisted here so we can prove compliance and
spot trends across releases.
"""
from django.conf import settings
from django.db import models


class FairnessAudit(models.Model):
    """Single audit run.

    ``passed`` is the gate output that CI consults via
    ``scripts/fairness_release_check.py``. ``violations`` is a list of
    explanatory entries mirroring what the auditor returned.
    """

    class AuditKind(models.TextChoices):
        CLASSIFIER = "classifier", "Classifier (DP / EOD)"
        CLUSTERING = "clustering", "Clustering (concentration)"
        REGRESSION = "regression", "Regression (group MSE)"

    target_name = models.CharField(
        max_length=120,
        help_text="Logical name of the model/cluster being audited (matches ModelRegistry.name when applicable).",
    )
    kind = models.CharField(max_length=20, choices=AuditKind.choices)
    sensitive_attributes = models.JSONField(
        default=list,
        help_text="List of attribute names checked (gender, region, economic_band, ...).",
    )
    metrics = models.JSONField(
        default=dict,
        help_text="Raw metric values: {disparate_impact_ratio, equalized_odds_diff, ...}",
    )
    violations = models.JSONField(
        default=list,
        help_text="List of {attr, value, observed, threshold} for failed checks.",
    )
    passed = models.BooleanField(default=False)
    sample_size = models.PositiveIntegerField(default=0)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fairness_audits_reviewed",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_fairness_audit"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["target_name", "-created_at"]),
            models.Index(fields=["passed", "-created_at"]),
        ]

    def __str__(self) -> str:
        verdict = "PASS" if self.passed else "FAIL"
        return f"[{verdict}] {self.target_name} ({self.kind})"
