"""
MLOps stack — model registry, versioning, drift detection, shadow deployment.

Lightweight in-house implementation that mirrors the contract of full
Feast/MLflow/Evidently stacks but lives entirely inside Postgres so PALP
can ship Phase 0 without committing to vendor infra. The optional
``MLFLOW_TRACKING_URI`` setting promotes the registry to a thin wrapper
over an external MLflow server when one becomes available.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class ModelRegistry(models.Model):
    """Logical model identity — many ``ModelVersion`` rows belong to one."""

    class ModelType(models.TextChoices):
        BKT = "bkt", "Bayesian Knowledge Tracing"
        DKT = "dkt", "Deep Knowledge Tracing"
        RISK_SCORE = "risk_score", "Risk Score Composite"
        SURVIVAL = "survival", "Dropout Survival"
        BANDIT = "bandit", "Contextual Bandit"
        AFFECT = "affect", "Affect Fusion"
        CLASSIFIER_OTHER = "classifier_other", "Classifier (other)"
        CLUSTERING = "clustering", "Clustering"
        EMBEDDING = "embedding", "Embedding"

    name = models.SlugField(max_length=80, unique=True)
    model_type = models.CharField(max_length=30, choices=ModelType.choices)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_models",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_mlops_registry"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_model_type_display()})"

    @property
    def production_version(self):
        return self.versions.filter(status=ModelVersion.Status.PRODUCTION).first()


class ModelVersion(models.Model):
    """Immutable artefact + metadata for a trained model."""

    class Status(models.TextChoices):
        TRAINING = "training", "Training"
        SHADOW = "shadow", "Shadow (eval only)"
        STAGING = "staging", "Staging (internal)"
        PRODUCTION = "production", "Production"
        DEPRECATED = "deprecated", "Deprecated"
        ARCHIVED = "archived", "Archived"

    registry = models.ForeignKey(
        ModelRegistry, on_delete=models.CASCADE, related_name="versions",
    )
    semver = models.CharField(
        max_length=20,
        help_text="Semantic version, e.g. 1.0.0",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.TRAINING,
    )
    artifact_uri = models.CharField(
        max_length=500, blank=True,
        help_text="MLflow artifact URI, S3 key, or local file path.",
    )
    metrics_json = models.JSONField(
        default=dict, blank=True,
        help_text="Quantitative results: {auc: 0.78, brier: 0.12, ...}.",
    )
    params_json = models.JSONField(
        default=dict, blank=True,
        help_text="Hyperparameters used for training.",
    )
    training_data_ref = models.CharField(
        max_length=300, blank=True,
        help_text="Pointer to training dataset version (Feast feature view + snapshot).",
    )
    fairness_passed = models.BooleanField(default=False)
    epsilon_dp = models.FloatField(
        null=True, blank=True,
        help_text="Differential-privacy epsilon spent during training (None if not DP).",
    )
    model_card_path = models.CharField(
        max_length=300, blank=True,
        help_text="Path to docs/model_cards/<name>.md.",
    )
    promoted_at = models.DateTimeField(null=True, blank=True)
    promoted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="promoted_model_versions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_mlops_version"
        constraints = [
            models.UniqueConstraint(
                fields=["registry", "semver"],
                name="uq_mlops_version_registry_semver",
            ),
        ]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["registry", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.registry.name}@{self.semver} [{self.status}]"


class FeatureView(models.Model):
    """Feast-compatible feature view declaration.

    Lightweight metadata only — actual feature data lives in source tables
    (SignalSession, MasteryState, etc.). Centralised registration lets
    downstream models (DKT, Bandit, RiskScore) declare their dependencies
    explicitly and lets us audit feature reuse.
    """

    name = models.SlugField(max_length=80, unique=True)
    entity = models.CharField(
        max_length=40,
        help_text="Logical entity: student, class, concept, etc.",
    )
    source_table = models.CharField(
        max_length=80,
        help_text="DB table that materialises this feature group.",
    )
    features_json = models.JSONField(
        default=list,
        help_text=(
            "List of feature spec dicts: "
            "[{name, dtype, description, ttl_seconds}]."
        ),
    )
    online_store_enabled = models.BooleanField(
        default=False,
        help_text="If True, hot reads served from Redis online store.",
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_mlops_feature_view"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.entity})"


class DriftReport(models.Model):
    """Periodic drift assessment for a model version.

    Generated by Celery (``mlops.tasks.run_drift_check``) using a small
    in-house equivalent of Evidently's data-drift report — KS / chi-square
    per feature, summarised to a single boolean ``drift_detected`` flag.
    """

    class Severity(models.TextChoices):
        NONE = "none", "Không drift"
        MINOR = "minor", "Drift nhẹ"
        MAJOR = "major", "Drift đáng kể"
        CRITICAL = "critical", "Drift nghiêm trọng — retrain ngay"

    model_version = models.ForeignKey(
        ModelVersion, on_delete=models.CASCADE, related_name="drift_reports",
    )
    window_start = models.DateTimeField()
    window_end = models.DateTimeField(default=timezone.now)
    drift_detected = models.BooleanField(default=False)
    severity = models.CharField(
        max_length=20, choices=Severity.choices, default=Severity.NONE,
    )
    feature_summary = models.JSONField(
        default=dict,
        help_text="Per-feature drift score: {feat_name: {ks_p, drift_score}}.",
    )
    sample_size = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_mlops_drift_report"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["model_version", "-created_at"]),
            models.Index(fields=["severity", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.model_version} drift={self.severity} @ {self.window_end:%Y-%m-%d}"


class ShadowComparison(models.Model):
    """Shadow deployment comparison record.

    Records prediction divergence between a candidate (shadow) version and
    the current production version on the same input. Aggregated nightly
    into ``divergence_summary`` to drive the cutover decision.
    """

    candidate_version = models.ForeignKey(
        ModelVersion,
        on_delete=models.CASCADE,
        related_name="shadow_runs_as_candidate",
    )
    baseline_version = models.ForeignKey(
        ModelVersion,
        on_delete=models.CASCADE,
        related_name="shadow_runs_as_baseline",
    )
    window_start = models.DateTimeField()
    window_end = models.DateTimeField(default=timezone.now)
    n_predictions = models.PositiveIntegerField(default=0)
    mean_abs_diff = models.FloatField(default=0.0)
    p95_abs_diff = models.FloatField(default=0.0)
    agreement_pct = models.FloatField(
        default=0.0,
        help_text="Percentage of predictions where shadow and baseline agree within ±0.05.",
    )
    divergence_summary = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_mlops_shadow_comparison"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["candidate_version", "-created_at"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.candidate_version} vs {self.baseline_version}: "
            f"agree {self.agreement_pct:.1%}"
        )
