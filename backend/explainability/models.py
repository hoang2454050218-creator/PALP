"""Explainability (XAI) models — Phase 6 of v3 MAXIMAL roadmap.

Persists the explanation any model produces so:

* The lecturer dashboard can show "why this student was flagged" without
  recomputing.
* GDPR Art.22 / NĐ 13/2023 audits have the artefact on file.
* Drift detection can compare explanation distributions over time.

The actual SHAP-lite / attention / counterfactual logic lives in
``explainability/engines/``; these models are model-agnostic so any
predictor (RiskScore, DKT, FSRS) can write through.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models


class ExplanationRecord(models.Model):
    """One explanation snapshot for one (subject, target) pair."""

    class Kind(models.TextChoices):
        RISK_SCORE = "risk_score", "Composite risk"
        DKT_PREDICTION = "dkt_prediction", "DKT next-correct"
        FSRS_REVIEW = "fsrs_review", "FSRS interval"
        BANDIT_DECISION = "bandit_decision", "Bandit arm choice"
        OTHER = "other", "Khác"

    class Method(models.TextChoices):
        SHAP_LITE = "shap_lite", "SHAP-lite (additive)"
        ATTENTION = "attention", "Attention weights"
        COUNTERFACTUAL = "counterfactual", "Counterfactual"
        RULE_TRACE = "rule_trace", "Rule trace"

    subject = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="explanations",
    )
    kind = models.CharField(max_length=24, choices=Kind.choices)
    method = models.CharField(max_length=24, choices=Method.choices)

    target_object_id = models.CharField(
        max_length=64, blank=True,
        help_text="Loose pointer to the predicted thing (concept_id, decision_id, …).",
    )
    summary = models.CharField(
        max_length=255,
        help_text="Short Vietnamese sentence the UI can show as the headline.",
    )
    payload = models.JSONField(
        default=dict, blank=True,
        help_text="Full explanation payload (contributions, attention rows, ...).",
    )
    confidence = models.FloatField(default=0.5)
    base_value = models.FloatField(
        null=True, blank=True,
        help_text="Population baseline (mean of the score) for additive methods.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_xai_explanation"
        indexes = [
            models.Index(fields=["subject", "kind", "-created_at"]),
            models.Index(fields=["kind", "method", "-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Explain({self.subject_id}, {self.kind}, {self.method})"


class FeatureContribution(models.Model):
    """One per (explanation, feature) — additive SHAP-lite row.

    Stored separately from ``payload`` so analytics can group / average /
    filter without parsing JSON. Optional — counterfactual /
    attention-only explanations don't need this.
    """

    explanation = models.ForeignKey(
        ExplanationRecord,
        on_delete=models.CASCADE,
        related_name="contributions",
    )
    feature_key = models.CharField(max_length=80)
    raw_value = models.FloatField(null=True, blank=True)
    contribution = models.FloatField(
        help_text="Signed contribution to the prediction. Positive = pushes UP.",
    )
    rank = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "palp_xai_feature_contribution"
        ordering = ["explanation", "rank"]
        indexes = [
            models.Index(fields=["explanation", "rank"]),
        ]

    def __str__(self) -> str:
        return f"FC({self.explanation_id}, {self.feature_key}={self.contribution:+.3f})"


class CounterfactualScenario(models.Model):
    """Persisted counterfactual: 'if X changed by Δ, prediction would shift by Y'."""

    explanation = models.ForeignKey(
        ExplanationRecord,
        on_delete=models.CASCADE,
        related_name="counterfactuals",
    )
    feature_key = models.CharField(max_length=80)
    current_value = models.FloatField()
    target_value = models.FloatField()
    expected_delta = models.FloatField()
    feasibility = models.FloatField(
        default=0.5,
        help_text="0..1 — how realistic is it for the student to make this change.",
    )
    actionable_hint = models.CharField(max_length=240, blank=True)

    class Meta:
        db_table = "palp_xai_counterfactual"
        indexes = [
            models.Index(fields=["explanation", "-expected_delta"]),
        ]

    def __str__(self) -> str:
        return (
            f"CF({self.explanation_id}, {self.feature_key}: "
            f"{self.current_value:.2f}→{self.target_value:.2f}, "
            f"Δ={self.expected_delta:+.3f})"
        )
