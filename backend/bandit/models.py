"""Contextual Multi-Armed Bandit models — Phase 5 of v3 MAXIMAL.

Implements the storage layer for a Beta-Bernoulli Thompson sampling
bandit. We deliberately keep the bandit "contextual" by indexing
(arm, context_key) so the same arm can have different posteriors per
context (e.g. nudge for high-risk vs low-risk students).

Why Beta-Bernoulli for the first ship:

* Closed-form posterior update — pure ``alpha += reward`` /
  ``beta += (1 - reward)``. No external optimiser, no PyTorch.
* Reward is 0/1 (engagement / no engagement) which fits the
  Bernoulli likelihood naturally.
* The exploration/exploitation balance is automatic via Thompson
  sampling — no hand-tuned epsilon.

LinUCB / Contextual NN bandits are added in Phase 5B once we have a
labelled outcome stream from this Beta-Bernoulli phase.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models


class BanditExperiment(models.Model):
    """A logical grouping of arms (e.g. "nudge_dispatch", "task_difficulty")."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Đang chạy"
        PAUSED = "paused", "Tạm dừng"
        ARCHIVED = "archived", "Đã lưu trữ"

    key = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE,
    )

    reward_window_minutes = models.PositiveIntegerField(
        default=24 * 60,
        help_text="How long after a decision we still accept reward signals.",
    )
    seed = models.PositiveIntegerField(
        default=42,
        help_text="RNG seed for reproducible Thompson sampling in tests.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_bandit_experiment"

    def __str__(self) -> str:
        return f"{self.key} [{self.status}]"


class BanditArm(models.Model):
    """One action option in a ``BanditExperiment``.

    Posteriors are stored per (arm, context_key) inside ``BanditPosterior``
    rather than on the arm itself, so the same arm can have different
    success rates depending on context (e.g. a nudge that works on
    Friday vs Monday).
    """

    experiment = models.ForeignKey(
        BanditExperiment, on_delete=models.CASCADE, related_name="arms",
    )
    key = models.SlugField(max_length=80)
    title = models.CharField(max_length=160)
    payload = models.JSONField(
        default=dict, blank=True,
        help_text="Arm-specific data the consumer needs (template_id, channel, …).",
    )
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_bandit_arm"
        constraints = [
            models.UniqueConstraint(
                fields=["experiment", "key"],
                name="uq_bandit_experiment_arm",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.experiment.key}/{self.key}"


class BanditPosterior(models.Model):
    """Beta(alpha, beta) posterior for one (arm, context_key) pair.

    Updated atomically via ``services.record_reward``. Initialised as
    ``Beta(1, 1)`` (uniform prior) the first time the arm is selected
    in a given context.
    """

    arm = models.ForeignKey(
        BanditArm, on_delete=models.CASCADE, related_name="posteriors",
    )
    context_key = models.CharField(
        max_length=80,
        default="default",
        help_text="Free-form context label (e.g. 'high_risk', 'morning').",
    )
    alpha = models.FloatField(default=1.0)
    beta = models.FloatField(default=1.0)

    pulls = models.PositiveIntegerField(default=0)
    rewards_sum = models.FloatField(default=0.0)
    last_pulled_at = models.DateTimeField(null=True, blank=True)
    last_rewarded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "palp_bandit_posterior"
        constraints = [
            models.UniqueConstraint(
                fields=["arm", "context_key"],
                name="uq_bandit_arm_context",
            ),
        ]
        indexes = [
            models.Index(fields=["arm", "context_key"]),
        ]

    def __str__(self) -> str:
        return (
            f"Posterior(arm={self.arm_id}, ctx={self.context_key}, "
            f"α={self.alpha:.2f}, β={self.beta:.2f})"
        )

    @property
    def expected_reward(self) -> float:
        total = self.alpha + self.beta
        return self.alpha / total if total > 0 else 0.0


class BanditDecision(models.Model):
    """One arm-selection event."""

    experiment = models.ForeignKey(
        BanditExperiment, on_delete=models.CASCADE, related_name="decisions",
    )
    arm = models.ForeignKey(
        BanditArm, on_delete=models.CASCADE, related_name="decisions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bandit_decisions",
    )
    context_key = models.CharField(max_length=80, default="default")
    sampled_value = models.FloatField(
        help_text="Thompson sample drawn from the posterior at decision time.",
    )
    decided_at = models.DateTimeField(auto_now_add=True)
    reward_window_until = models.DateTimeField(
        null=True, blank=True,
        help_text="Reward signals after this time are ignored.",
    )

    class Meta:
        db_table = "palp_bandit_decision"
        indexes = [
            models.Index(fields=["user", "-decided_at"]),
            models.Index(fields=["experiment", "-decided_at"]),
        ]

    def __str__(self) -> str:
        return f"Decision({self.experiment.key}/{self.arm.key} -> u={self.user_id})"


class BanditReward(models.Model):
    """Reward signal attached to a decision."""

    decision = models.OneToOneField(
        BanditDecision, on_delete=models.CASCADE, related_name="reward",
    )
    value = models.FloatField(
        help_text="0.0 (no engagement) .. 1.0 (full engagement).",
    )
    notes = models.CharField(max_length=255, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_bandit_reward"

    def __str__(self) -> str:
        return f"Reward(decision={self.decision_id}, v={self.value:.2f})"


class LinUCBArmState(models.Model):
    """Persisted (A, b) per (arm, context_key) for LinUCB.

    Stored as JSON so we don't need a vector column type; pure-NumPy
    LinUCB engine reconstructs ``np.ndarray`` on read. Phase 7
    addition — additive, lives alongside Beta-Bernoulli.
    """

    arm = models.ForeignKey(
        BanditArm, on_delete=models.CASCADE, related_name="linucb_states",
    )
    context_key = models.CharField(max_length=80, default="default")
    dimension = models.PositiveSmallIntegerField()
    matrix_a = models.JSONField(
        help_text="Serialised d-by-d matrix A_a (NumPy .tolist()).",
    )
    vector_b = models.JSONField(
        help_text="Serialised length-d vector b_a (NumPy .tolist()).",
    )
    pulls = models.PositiveIntegerField(default=0)
    rewards_sum = models.FloatField(default=0.0)
    last_pulled_at = models.DateTimeField(null=True, blank=True)
    last_rewarded_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_bandit_linucb_state"
        constraints = [
            models.UniqueConstraint(
                fields=["arm", "context_key"],
                name="uq_bandit_linucb_arm_context",
            ),
        ]
        indexes = [
            models.Index(fields=["arm", "context_key"]),
        ]

    def __str__(self) -> str:
        return f"LinUCB({self.arm_id}, ctx={self.context_key}, d={self.dimension})"
