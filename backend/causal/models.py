"""
Causal inference layer that augments ``experiments.Experiment`` with the
methodological rigour required by Phase 0 of the v3 roadmap.

A ``CausalExperiment`` row is **always** linked to an
``experiments.Experiment`` (which provides the variant + assignment
plumbing). The causal layer adds:

* Pre-registration enforcement (hypothesis, outcome, analysis method
  recorded with timestamp before the experiment runs).
* Power-analysis bookkeeping.
* IRB tracking.
* Persisted ``CausalEvaluation`` rows that store ATE/uplift estimates
  produced by the various estimators (Naive / IPW / Doubly-Robust / CUPED).

The actual estimation logic lives in ``causal.uplift``, ``causal.cuped``,
and ``causal.doubly_robust`` so this module remains pure data layer.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class CausalExperiment(models.Model):
    """Pre-registered causal experiment metadata.

    The ``experiment`` FK gives us all the A/B plumbing already shipped
    in ``experiments``; this row layers on top with the science contract.
    """

    class OutcomeKind(models.TextChoices):
        BINARY = "binary", "Binary (0/1)"
        CONTINUOUS = "continuous", "Continuous"
        TIME_TO_EVENT = "time_to_event", "Time-to-event"

    class RandomizationUnit(models.TextChoices):
        STUDENT = "student", "Per-student (default)"
        CLASS = "class", "Per-class (cluster RCT)"
        COHORT = "cohort", "Per-cohort"
        TIME_SLICE = "time_slice", "Time-slice (switchback)"

    experiment = models.OneToOneField(
        "experiments.Experiment",
        on_delete=models.CASCADE,
        related_name="causal_layer",
        help_text="Underlying A/B experiment that supplies variants + assignments.",
    )
    pre_registration = models.TextField(
        help_text=(
            "Frozen statement of hypothesis + primary outcome + analysis method, "
            "captured BEFORE the experiment is started. Modifying this after "
            "``locked_at`` is set requires a new amendment."
        ),
    )
    primary_outcome_metric = models.CharField(
        max_length=120,
        help_text="Name of the KPI used as primary outcome.",
    )
    secondary_outcomes = models.JSONField(
        default=list, blank=True,
        help_text="List of additional outcome metric names.",
    )
    outcome_kind = models.CharField(
        max_length=20, choices=OutcomeKind.choices, default=OutcomeKind.CONTINUOUS,
    )
    randomization_unit = models.CharField(
        max_length=20,
        choices=RandomizationUnit.choices,
        default=RandomizationUnit.STUDENT,
    )
    cuped_covariate = models.CharField(
        max_length=120, blank=True,
        help_text="Optional pre-period metric used for CUPED variance reduction.",
    )
    expected_effect_size = models.FloatField(
        null=True, blank=True,
        help_text="Effect size used in the power analysis.",
    )
    target_sample_per_arm = models.PositiveIntegerField(default=0)
    irb_reference = models.CharField(
        max_length=80, blank=True,
        help_text="IRB approval ID. Required for studies with human-subjects causal claims.",
    )

    locked_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Set when ``lock_pre_registration()`` is called. After this, "
                  "any change to hypothesis/outcome/method must use ``amendments_log``.",
    )
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="causal_pre_registrations",
    )
    amendments_log = models.JSONField(
        default=list, blank=True,
        help_text="Append-only list of {when, by, reason, diff} after lock.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_causal_experiment"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        lock_state = "LOCKED" if self.locked_at else "draft"
        return f"[{lock_state}] {self.experiment.name} — {self.primary_outcome_metric}"

    @property
    def is_locked(self) -> bool:
        return self.locked_at is not None

    def lock(self, by=None):
        if self.is_locked:
            raise ValueError("Pre-registration already locked.")
        self.locked_at = timezone.now()
        self.locked_by = by
        self.save(update_fields=["locked_at", "locked_by"])

    def amend(self, *, reason: str, diff: dict, by=None):
        if not self.is_locked:
            raise ValueError(
                "Amendments only apply after lock. Edit fields directly while in draft."
            )
        entry = {
            "when": timezone.now().isoformat(),
            "by": getattr(by, "username", None),
            "reason": reason,
            "diff": diff,
        }
        self.amendments_log = list(self.amendments_log or []) + [entry]
        self.save(update_fields=["amendments_log"])


class CausalEvaluation(models.Model):
    """Result of a single estimator run for a ``CausalExperiment``.

    Multiple evaluations per experiment are expected (one per estimator,
    plus interim looks). All raw numeric outputs are stored in
    ``estimate_json`` so we don't need to migrate the schema for every
    new estimator we try.
    """

    class Estimator(models.TextChoices):
        NAIVE = "naive", "Naive difference-in-means"
        IPW = "ipw", "Inverse Propensity Weighting"
        DOUBLY_ROBUST = "doubly_robust", "Doubly-Robust"
        CUPED_NAIVE = "cuped_naive", "Naive + CUPED variance reduction"
        UPLIFT_TREE = "uplift_tree", "Uplift forest (causalml)"

    experiment = models.ForeignKey(
        CausalExperiment, on_delete=models.CASCADE, related_name="evaluations",
    )
    estimator = models.CharField(max_length=30, choices=Estimator.choices)
    n_treatment = models.PositiveIntegerField(default=0)
    n_control = models.PositiveIntegerField(default=0)
    ate = models.FloatField(null=True, blank=True)
    ate_ci_low = models.FloatField(null=True, blank=True)
    ate_ci_high = models.FloatField(null=True, blank=True)
    p_value = models.FloatField(null=True, blank=True)
    estimate_json = models.JSONField(
        default=dict, blank=True,
        help_text="Estimator-specific extras (heterogeneity table, std errors, ...).",
    )
    fairness_audit_id = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="FK-style reference to fairness.FairnessAudit so we can prove "
                  "subgroup fairness was checked alongside the causal claim. "
                  "Plain integer to avoid hard-coupling apps.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_causal_evaluation"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["experiment", "estimator"]),
        ]

    def __str__(self) -> str:
        return f"{self.experiment.experiment.name} — {self.estimator} ATE={self.ate}"
