"""
Feature flags model.

Self-host alternative to Unleash / LaunchDarkly tailored to PALP scale.
Decisions are deterministic per (flag, user) so a student always sees the
same variant across navigation, while researchers can roll out gradually
or target specific roles.

Audit log captures every change with before/after diff for compliance.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class FeatureFlag(models.Model):
    """A single feature toggle.

    ``rollout_pct`` is computed against a stable hash of the user id so the
    rollout is consistent across navigations. ``rules_json`` allows targeted
    rollout (specific roles, classes, environments).
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Dot-namespaced identifier, e.g. 'pedagogy.adaptive_difficulty_v2'.",
    )
    description = models.TextField(blank=True)
    enabled = models.BooleanField(
        default=False,
        help_text="Master switch. When False the flag is OFF for everyone.",
    )
    rollout_pct = models.PositiveSmallIntegerField(
        default=0,
        help_text="0-100. Deterministic per user id when enabled=True.",
    )
    rules_json = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Optional targeting: "
            "{'roles': ['student'], 'class_ids': [12], 'env': ['staging']}."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_feature_flag"
        ordering = ["name"]

    def __str__(self) -> str:
        state = "ON" if self.enabled else "OFF"
        return f"[{state} {self.rollout_pct}%] {self.name}"


class FeatureFlagAudit(models.Model):
    """Immutable change log for compliance + forensic debugging."""

    flag = models.ForeignKey(
        FeatureFlag, on_delete=models.CASCADE, related_name="audit_entries",
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="flag_changes",
    )
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    when = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "palp_feature_flag_audit"
        ordering = ["-when"]
