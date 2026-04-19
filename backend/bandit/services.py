"""Bandit service layer — DB-aware Thompson sampling + reward update.

Beta-Bernoulli is the baseline; LinUCB lives alongside it for
contextual problems where a continuous feature vector is available.
The two paths share the ``BanditDecision`` / ``BanditReward`` tables
so downstream consumers (analytics, dashboards) treat them uniformly.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Sequence

import numpy as np
from django.db import transaction
from django.utils import timezone

from bandit.engine import (
    ArmPosteriorState,
    ThompsonChoice,
    thompson_select,
    update_posterior,
)
from bandit.linucb import (
    LinUCBArmState as LinUCBArmStateNP,
    LinUCBChoice,
    select as linucb_select,
    update as linucb_update,
)
from bandit.models import (
    BanditArm,
    BanditDecision,
    BanditExperiment,
    BanditPosterior,
    BanditReward,
    LinUCBArmState,
)


@dataclass
class SelectResult:
    decision: BanditDecision
    arm: BanditArm
    sampled_value: float
    samples: dict[int, float]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@transaction.atomic
def select_arm(
    *,
    experiment_key: str,
    user,
    context_key: str = "default",
    rng_seed_extra: int = 0,
) -> SelectResult:
    """Pick an arm via Thompson sampling and persist the decision."""
    experiment = BanditExperiment.objects.select_for_update().get(key=experiment_key)
    if experiment.status != BanditExperiment.Status.ACTIVE:
        raise BanditExperimentInactive(experiment_key)

    arms = list(
        experiment.arms.filter(is_enabled=True).order_by("id")
    )
    if not arms:
        raise NoEnabledArms(experiment_key)

    posteriors: list[ArmPosteriorState] = []
    posterior_rows: dict[int, BanditPosterior] = {}
    for arm in arms:
        post, _ = BanditPosterior.objects.select_for_update().get_or_create(
            arm=arm, context_key=context_key,
        )
        posteriors.append(
            ArmPosteriorState(
                arm_id=arm.id, alpha=float(post.alpha), beta=float(post.beta),
            )
        )
        posterior_rows[arm.id] = post

    rng = np.random.default_rng(experiment.seed + user.id + rng_seed_extra)
    choice: ThompsonChoice = thompson_select(posteriors=posteriors, rng=rng)

    chosen_arm = next(a for a in arms if a.id == choice.arm_id)

    now = timezone.now()
    decision = BanditDecision.objects.create(
        experiment=experiment,
        arm=chosen_arm,
        user=user,
        context_key=context_key,
        sampled_value=choice.sampled_value,
        reward_window_until=now + timedelta(minutes=experiment.reward_window_minutes),
    )

    posterior_rows[choice.arm_id].pulls += 1
    posterior_rows[choice.arm_id].last_pulled_at = now
    posterior_rows[choice.arm_id].save(update_fields=["pulls", "last_pulled_at"])

    return SelectResult(
        decision=decision,
        arm=chosen_arm,
        sampled_value=choice.sampled_value,
        samples=choice.samples,
    )


@transaction.atomic
def record_reward(*, decision: BanditDecision, value: float, notes: str = "") -> BanditReward:
    """Attach a reward signal and update the corresponding posterior."""
    if hasattr(decision, "reward"):
        return decision.reward

    if (
        decision.reward_window_until is not None
        and decision.reward_window_until < timezone.now()
    ):
        # Stale signal — record it but DON'T update the posterior to
        # keep the model honest (the playbook spells this out).
        return BanditReward.objects.create(
            decision=decision,
            value=max(0.0, min(1.0, float(value))),
            notes=(notes + " [stale_window_ignored]").strip(),
        )

    reward = BanditReward.objects.create(
        decision=decision,
        value=max(0.0, min(1.0, float(value))),
        notes=notes,
    )

    post = (
        BanditPosterior.objects
        .select_for_update()
        .get(arm=decision.arm, context_key=decision.context_key)
    )
    new_alpha, new_beta = update_posterior(
        alpha=post.alpha, beta=post.beta, reward=reward.value,
    )
    post.alpha = new_alpha
    post.beta = new_beta
    post.rewards_sum = float(post.rewards_sum) + reward.value
    post.last_rewarded_at = timezone.now()
    post.save(update_fields=["alpha", "beta", "rewards_sum", "last_rewarded_at"])
    return reward


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class BanditError(Exception):
    pass


class BanditExperimentInactive(BanditError):
    pass


class NoEnabledArms(BanditError):
    pass


# ---------------------------------------------------------------------------
# LinUCB — additive Phase 7 path
# ---------------------------------------------------------------------------

@dataclass
class LinUCBSelectResult:
    decision: BanditDecision
    arm: BanditArm
    score: float
    confidence: float
    means: dict[int, float]
    bounds: dict[int, float]


def _ensure_linucb_state(arm: BanditArm, *, context_key: str, dimension: int) -> LinUCBArmState:
    state, created = LinUCBArmState.objects.select_for_update().get_or_create(
        arm=arm,
        context_key=context_key,
        defaults={
            "dimension": dimension,
            "matrix_a": np.eye(dimension).tolist(),
            "vector_b": np.zeros(dimension).tolist(),
        },
    )
    if not created and state.dimension != dimension:
        raise ValueError(
            f"LinUCB state for arm {arm.id}/{context_key} has dim "
            f"{state.dimension}, caller provided d={dimension}."
        )
    return state


@transaction.atomic
def select_arm_linucb(
    *,
    experiment_key: str,
    user,
    context: Sequence[float],
    context_key: str = "default",
    alpha: float = 1.0,
) -> LinUCBSelectResult:
    """Pick an arm via LinUCB and persist the decision."""
    experiment = BanditExperiment.objects.select_for_update().get(key=experiment_key)
    if experiment.status != BanditExperiment.Status.ACTIVE:
        raise BanditExperimentInactive(experiment_key)

    arms = list(experiment.arms.filter(is_enabled=True).order_by("id"))
    if not arms:
        raise NoEnabledArms(experiment_key)

    dimension = len(context)
    states_db = [
        _ensure_linucb_state(arm, context_key=context_key, dimension=dimension)
        for arm in arms
    ]
    states_np = [
        LinUCBArmStateNP.from_dict({
            "arm_id": s.arm_id, "A": s.matrix_a, "b": s.vector_b,
        })
        for s in states_db
    ]

    choice: LinUCBChoice = linucb_select(
        states=states_np, context=context, alpha=alpha,
    )

    chosen_arm = next(a for a in arms if a.id == choice.arm_id)
    chosen_state = next(s for s in states_db if s.arm_id == choice.arm_id)

    now = timezone.now()
    decision = BanditDecision.objects.create(
        experiment=experiment,
        arm=chosen_arm,
        user=user,
        context_key=context_key,
        sampled_value=float(choice.score),
        reward_window_until=now + timedelta(minutes=experiment.reward_window_minutes),
    )

    chosen_state.pulls += 1
    chosen_state.last_pulled_at = now
    chosen_state.save(update_fields=["pulls", "last_pulled_at"])

    return LinUCBSelectResult(
        decision=decision,
        arm=chosen_arm,
        score=float(choice.score),
        confidence=float(choice.confidence_term),
        means=choice.means,
        bounds=choice.bounds,
    )


@transaction.atomic
def record_reward_linucb(
    *,
    decision: BanditDecision,
    context: Sequence[float],
    value: float,
    notes: str = "",
) -> BanditReward:
    """LinUCB reward path. Caller must supply the same ``context`` used at decision time."""
    if hasattr(decision, "reward"):
        return decision.reward
    if (
        decision.reward_window_until is not None
        and decision.reward_window_until < timezone.now()
    ):
        return BanditReward.objects.create(
            decision=decision,
            value=max(0.0, min(1.0, float(value))),
            notes=(notes + " [stale_window_ignored]").strip(),
        )
    reward = BanditReward.objects.create(
        decision=decision,
        value=max(0.0, min(1.0, float(value))),
        notes=notes,
    )
    state = LinUCBArmState.objects.select_for_update().get(
        arm=decision.arm, context_key=decision.context_key,
    )
    np_state = LinUCBArmStateNP.from_dict({
        "arm_id": state.arm_id,
        "A": state.matrix_a,
        "b": state.vector_b,
    })
    updated = linucb_update(np_state, context=context, reward=reward.value)
    state.matrix_a = updated.A.tolist()
    state.vector_b = updated.b.tolist()
    state.rewards_sum = float(state.rewards_sum) + reward.value
    state.last_rewarded_at = timezone.now()
    state.save(update_fields=["matrix_a", "vector_b", "rewards_sum", "last_rewarded_at"])
    return reward
