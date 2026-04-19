"""Differential Privacy models — Phase 6 of v3 MAXIMAL roadmap.

Tracks per-(scope, period) ε-budgets and logs each DP query that
spends from them. The Laplace mechanism + budget enforcement live in
``privacy_dp/engine.py``.

Why we ship this NOW even though we don't yet release any DP
analytics: we want the budget bookkeeping in place BEFORE the first
DP query lands so Phase 6B (the actual public analytics endpoints)
can flip a flag without retro-engineering audit history.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models


class EpsilonBudget(models.Model):
    """Total ε allowed for one (scope, period) bucket.

    ``scope`` is a free-form key like ``class:42:weekly`` or
    ``global:monthly``; the engine enforces uniqueness so two
    schedulers can't double-spend.
    """

    scope = models.SlugField(max_length=120)
    period_start = models.DateField()
    period_end = models.DateField()
    epsilon_total = models.FloatField(
        default=1.0,
        help_text="Maximum cumulative ε allowed within the period.",
    )
    epsilon_spent = models.FloatField(default=0.0)
    description = models.CharField(max_length=240, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_dp_epsilon_budget"
        constraints = [
            models.UniqueConstraint(
                fields=["scope", "period_start"],
                name="uq_dp_epsilon_scope_period",
            ),
        ]
        indexes = [
            models.Index(fields=["scope", "-period_start"]),
        ]

    def __str__(self) -> str:
        return (
            f"EpsBudget({self.scope}, {self.period_start}, "
            f"spent={self.epsilon_spent:.3f}/{self.epsilon_total:.3f})"
        )

    @property
    def remaining(self) -> float:
        return max(0.0, float(self.epsilon_total) - float(self.epsilon_spent))


class DPQueryLog(models.Model):
    """Append-only log of DP queries the system has answered."""

    class Mechanism(models.TextChoices):
        LAPLACE = "laplace", "Laplace"
        GAUSSIAN = "gaussian", "Gaussian"

    budget = models.ForeignKey(
        EpsilonBudget,
        on_delete=models.PROTECT,
        related_name="queries",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="dp_queries",
    )
    mechanism = models.CharField(
        max_length=16, choices=Mechanism.choices, default=Mechanism.LAPLACE,
    )
    query_kind = models.CharField(max_length=80)
    epsilon_spent = models.FloatField()
    sensitivity = models.FloatField(default=1.0)
    raw_value = models.FloatField()
    noisy_value = models.FloatField()
    sample_size = models.PositiveIntegerField(default=0)
    notes = models.CharField(max_length=240, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_dp_query_log"
        indexes = [
            models.Index(fields=["budget", "-created_at"]),
            models.Index(fields=["query_kind", "-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return (
            f"DPQuery({self.query_kind}, ε={self.epsilon_spent:.3f}, "
            f"raw={self.raw_value:.2f}, noisy={self.noisy_value:.2f})"
        )
