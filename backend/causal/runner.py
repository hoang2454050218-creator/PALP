"""
``ExperimentRunner`` — orchestrates a CausalExperiment.

Workflow:
1. ``register(experiment, ...)`` creates the ``CausalExperiment`` row in
   draft state.
2. Researchers fill in pre-registration text + outcomes.
3. ``lock(experiment, by=user)`` freezes the contract — after this any
   change goes through ``amend()``.
4. The underlying ``experiments.Experiment`` is started (``status=running``)
   so users start receiving variant assignments.
5. After data accumulates, ``evaluate(experiment, estimator=..., ...)``
   pulls outcome data, runs the estimator, persists a ``CausalEvaluation``,
   and optionally cross-references a ``FairnessAudit``.
"""
from __future__ import annotations

import logging
from typing import Iterable

from django.db import transaction

from experiments.models import Experiment

from .estimators import cuped_ate, doubly_robust_ate, ipw_ate, naive_ate
from .models import CausalEvaluation, CausalExperiment

logger = logging.getLogger("palp")


class PreRegistrationError(ValueError):
    """Raised when the pre-registration contract is violated."""


def register(
    *,
    experiment: Experiment,
    pre_registration: str,
    primary_outcome_metric: str,
    secondary_outcomes: list[str] | None = None,
    outcome_kind: str = CausalExperiment.OutcomeKind.CONTINUOUS,
    randomization_unit: str = CausalExperiment.RandomizationUnit.STUDENT,
    cuped_covariate: str = "",
    expected_effect_size: float | None = None,
    target_sample_per_arm: int = 0,
    irb_reference: str = "",
) -> CausalExperiment:
    """Create the causal layer for an existing ``experiments.Experiment``."""
    obj, created = CausalExperiment.objects.get_or_create(
        experiment=experiment,
        defaults={
            "pre_registration": pre_registration,
            "primary_outcome_metric": primary_outcome_metric,
            "secondary_outcomes": secondary_outcomes or [],
            "outcome_kind": outcome_kind,
            "randomization_unit": randomization_unit,
            "cuped_covariate": cuped_covariate,
            "expected_effect_size": expected_effect_size,
            "target_sample_per_arm": target_sample_per_arm,
            "irb_reference": irb_reference,
        },
    )
    if not created:
        if obj.is_locked:
            raise PreRegistrationError(
                "Cannot re-register a locked CausalExperiment; use amend() instead."
            )
        # Allow redefining while in draft.
        obj.pre_registration = pre_registration
        obj.primary_outcome_metric = primary_outcome_metric
        obj.secondary_outcomes = secondary_outcomes or []
        obj.outcome_kind = outcome_kind
        obj.randomization_unit = randomization_unit
        obj.cuped_covariate = cuped_covariate
        obj.expected_effect_size = expected_effect_size
        obj.target_sample_per_arm = target_sample_per_arm
        obj.irb_reference = irb_reference
        obj.save()
    return obj


def lock(experiment: CausalExperiment, *, by=None) -> CausalExperiment:
    if not experiment.pre_registration.strip():
        raise PreRegistrationError("Pre-registration text must not be empty before locking.")
    if not experiment.primary_outcome_metric.strip():
        raise PreRegistrationError("Primary outcome must be set before locking.")
    if experiment.expected_effect_size is None or experiment.target_sample_per_arm == 0:
        raise PreRegistrationError("Power analysis (effect size + target N per arm) required before lock.")
    experiment.lock(by=by)
    logger.info(
        "CausalExperiment locked",
        extra={"experiment": experiment.experiment.name, "by": getattr(by, "username", "system")},
    )
    return experiment


@transaction.atomic
def evaluate(
    experiment: CausalExperiment,
    *,
    y: Iterable[float],
    treatment: Iterable[int],
    estimator: str = CausalEvaluation.Estimator.NAIVE,
    pre_covariate: Iterable[float] | None = None,
    propensity: Iterable[float] | None = None,
    mu_treatment: Iterable[float] | None = None,
    mu_control: Iterable[float] | None = None,
    fairness_audit_id: int | None = None,
    extra: dict | None = None,
) -> CausalEvaluation:
    """Run an estimator over outcome data and persist the result."""
    if not experiment.is_locked:
        raise PreRegistrationError(
            "Refusing to evaluate before pre-registration is locked."
        )

    if estimator == CausalEvaluation.Estimator.NAIVE:
        result = naive_ate(y, treatment)
    elif estimator == CausalEvaluation.Estimator.CUPED_NAIVE:
        if pre_covariate is None:
            raise ValueError("CUPED estimator requires pre_covariate.")
        result = cuped_ate(y, treatment, pre_covariate)
    elif estimator == CausalEvaluation.Estimator.IPW:
        if propensity is None:
            raise ValueError("IPW estimator requires propensity.")
        result = ipw_ate(y, treatment, propensity)
    elif estimator == CausalEvaluation.Estimator.DOUBLY_ROBUST:
        if propensity is None or mu_treatment is None or mu_control is None:
            raise ValueError("DR estimator requires propensity + mu_treatment + mu_control.")
        result = doubly_robust_ate(y, treatment, propensity, mu_treatment, mu_control)
    elif estimator == CausalEvaluation.Estimator.UPLIFT_TREE:
        # Heavy dep — caller is expected to compute uplift externally and pass via extra.
        if not extra:
            raise ValueError("Uplift tree results must be supplied via 'extra'.")
        result = {"ate": extra.get("ate"), "estimator": "uplift_tree"}
    else:
        raise ValueError(f"Unknown estimator: {estimator!r}")

    evaluation = CausalEvaluation.objects.create(
        experiment=experiment,
        estimator=estimator,
        n_treatment=result.get("n_treatment", 0),
        n_control=result.get("n_control", 0),
        ate=result.get("ate"),
        ate_ci_low=result.get("ate_ci_low"),
        ate_ci_high=result.get("ate_ci_high"),
        p_value=result.get("p_value"),
        estimate_json={**result, **(extra or {})},
        fairness_audit_id=fairness_audit_id,
    )
    return evaluation
