"""
BKT v2 — context-aware Bayesian Knowledge Tracing.

Extends the classic 4-parameter BKT by injecting two attempt-level
modifiers before the Bayes update:

* **Time penalty.** A correct answer submitted in 3x the expected time
  carries less evidence of mastery than a quick correct answer; we
  scale ``effective_correct`` toward 0.5 (uninformative prior) when the
  response time is far above expected.
* **Hint penalty.** Every hint used reduces the credibility of a correct
  answer because the student leaned on the system. Each hint multiplies
  the ``effective_correct`` weight by ``(1 - HINT_PENALTY)``.

The result is a *fractional* observation in ``[0, 1]`` that we feed into
the standard BKT update by linearly blending the posterior between the
"saw correct" and "saw incorrect" cases. This stays mathematically
defensible — when ``effective_correct == 1`` we recover the classic
BKT correct update, when ``== 0`` we recover the incorrect update.

Auto-tune (Phase 1D weekly Celery task ``adaptive.tasks.bkt_autotune``)
fits ``p_guess`` and ``p_slip`` per concept from the last 30 days of
attempts using a beta-binomial Bayesian update around the
``PALP_BKT_DEFAULTS`` prior. Tuning runs in shadow first
(``mlops.shadow``) before being promoted.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Iterable

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q

from .engine import BKT_DEFAULTS, _cache_key, get_mastery_state
from .models import MasteryState, TaskAttempt

logger = logging.getLogger("palp")

DEFAULT_HINT_PENALTY = 0.25  # each hint shaves 25% of the credit
DEFAULT_TIME_OUTLIER_RATIO = 2.0  # > 2x expected -> response is "slow"
DEFAULT_TIME_PENALTY_FLOOR = 0.4  # don't shrink credit below this fraction


@dataclass
class AttemptContext:
    """Runtime input to the v2 update.

    ``expected_response_time_ms`` is optional; without it the time
    penalty is skipped entirely (so a missing field never makes the
    estimator MORE pessimistic).
    """

    is_correct: bool
    response_time_ms: int | None = None
    expected_response_time_ms: int | None = None
    hints_used: int = 0
    difficulty: int | None = None


def effective_correct(ctx: AttemptContext) -> float:
    """Map an AttemptContext to a fractional observation in [0, 1].

    Pure function; tested without DB access.
    """
    if not ctx.is_correct:
        return 0.0

    weight = 1.0
    if ctx.hints_used and ctx.hints_used > 0:
        weight *= max(0.0, (1 - DEFAULT_HINT_PENALTY) ** int(ctx.hints_used))

    if ctx.response_time_ms and ctx.expected_response_time_ms and ctx.expected_response_time_ms > 0:
        ratio = ctx.response_time_ms / ctx.expected_response_time_ms
        if ratio >= DEFAULT_TIME_OUTLIER_RATIO:
            # Smoothly decay credit between 1.0 (at ratio == 2) and
            # DEFAULT_TIME_PENALTY_FLOOR (at ratio >= 4).
            decay_span = max(1e-6, 4.0 - DEFAULT_TIME_OUTLIER_RATIO)
            decay = max(0.0, min(1.0, (ratio - DEFAULT_TIME_OUTLIER_RATIO) / decay_span))
            penalty = decay * (1 - DEFAULT_TIME_PENALTY_FLOOR)
            weight *= (1 - penalty)

    return max(0.0, min(1.0, weight))


def _bkt_posterior(p_l: float, p_g: float, p_s: float, p_t: float, observed_correct: float) -> float:
    """Fractional-observation BKT update.

    Linearly interpolates the standard BKT posterior between the "saw
    correct" branch (when ``observed_correct == 1``) and the "saw
    incorrect" branch (when ``observed_correct == 0``). For
    intermediate values we get a weighted mix. Mathematically equivalent
    to the standard formulation in the bookend cases.
    """
    # P(L | correct)
    correct_num = p_l * (1 - p_s)
    correct_den = correct_num + (1 - p_l) * p_g
    p_l_given_correct = correct_num / correct_den if correct_den > 0 else p_l

    # P(L | incorrect)
    wrong_num = p_l * p_s
    wrong_den = wrong_num + (1 - p_l) * (1 - p_g)
    p_l_given_wrong = wrong_num / wrong_den if wrong_den > 0 else p_l

    p_l_post = observed_correct * p_l_given_correct + (1 - observed_correct) * p_l_given_wrong
    p_l_new = p_l_post + (1 - p_l_post) * p_t
    return max(0.01, min(0.99, p_l_new))


@transaction.atomic
def update_mastery_v2(student_id: int, concept_id: int, ctx: AttemptContext) -> MasteryState:
    """Apply the v2 update.

    Persists into ``MasteryState.p_mastery_v2`` (NOT the legacy
    ``p_mastery``) so the v1 engine keeps producing baseline results
    during shadow deployment. ``risk.scoring`` and ``dashboard`` keep
    consuming ``p_mastery`` until the cutover gate.
    """
    cache.delete(_cache_key(student_id, concept_id))
    state = get_mastery_state(student_id, concept_id, for_update=True)

    p_l_baseline = state.p_mastery_v2 if state.p_mastery_v2 is not None else state.p_mastery
    obs = effective_correct(ctx)
    p_l_new = _bkt_posterior(
        p_l=p_l_baseline,
        p_g=state.p_guess,
        p_s=state.p_slip,
        p_t=state.p_transit,
        observed_correct=obs,
    )

    state.p_mastery_v2 = round(p_l_new, 6)
    state.save(update_fields=["p_mastery_v2", "last_updated"])

    logger.debug(
        "BKT v2: student=%s concept=%s correct=%s eff=%.3f P(L): %.3f -> %.3f",
        student_id, concept_id, ctx.is_correct, obs, p_l_baseline, p_l_new,
    )
    return state


# ---------------------------------------------------------------------------
# Auto-tuning (Phase 1D weekly Celery)
# ---------------------------------------------------------------------------


def _beta_update(prior_alpha: float, prior_beta: float, successes: int, failures: int) -> float:
    """Beta-binomial mean: (alpha + s) / (alpha + beta + s + f)."""
    return (prior_alpha + successes) / (prior_alpha + prior_beta + successes + failures)


def autotune_concept(concept_id: int, attempts: Iterable[TaskAttempt]) -> dict:
    """Update p_guess / p_slip for one concept from recent attempts.

    Returns a dict with the tuned values. Caller decides whether to write
    them back into MasteryState rows (we typically run this in shadow first).

    Heuristic split:
      * Among attempts where the student's prior P(L) was LOW (<= 0.4) we
        treat correct answers as evidence of "guess" (since the student
        likely didn't know).
      * Among attempts where the student's prior P(L) was HIGH (>= 0.8) we
        treat incorrect answers as evidence of "slip".

    Both buckets are folded into Beta-binomial updates rooted at
    ``PALP_BKT_DEFAULTS`` (acting as a soft prior with effective sample
    size 10) so a thin sample doesn't dominate the new estimate.
    """
    defaults = settings.PALP_BKT_DEFAULTS
    prior_strength = 10  # effective sample size for the prior

    p_g_prior = defaults["P_GUESS"]
    p_s_prior = defaults["P_SLIP"]

    g_alpha = p_g_prior * prior_strength
    g_beta = (1 - p_g_prior) * prior_strength
    s_alpha = p_s_prior * prior_strength
    s_beta = (1 - p_s_prior) * prior_strength

    n_low_correct = n_low_total = 0
    n_high_wrong = n_high_total = 0

    for attempt in attempts:
        # Use the v1 mastery at attempt time as the bucket label;
        # if missing, skip rather than guess (defensive).
        prior = MasteryState.objects.filter(
            student_id=attempt.student_id,
            concept_id=concept_id,
        ).values_list("p_mastery", flat=True).first()
        if prior is None:
            continue
        if prior <= 0.4:
            n_low_total += 1
            if attempt.is_correct:
                n_low_correct += 1
        elif prior >= 0.8:
            n_high_total += 1
            if not attempt.is_correct:
                n_high_wrong += 1

    new_p_g = _beta_update(g_alpha, g_beta, n_low_correct, max(0, n_low_total - n_low_correct))
    new_p_s = _beta_update(s_alpha, s_beta, n_high_wrong, max(0, n_high_total - n_high_wrong))

    # Hard invariants (carry over from existing engine).
    if new_p_g + new_p_s >= 1.0:
        # Shrink both back toward defaults to satisfy guess+slip < 1.
        new_p_g = (new_p_g + p_g_prior) / 2
        new_p_s = (new_p_s + p_s_prior) / 2

    return {
        "concept_id": concept_id,
        "n_low_total": n_low_total,
        "n_high_total": n_high_total,
        "p_guess": round(max(0.01, min(0.99, new_p_g)), 4),
        "p_slip": round(max(0.01, min(0.99, new_p_s)), 4),
        "prior_p_guess": p_g_prior,
        "prior_p_slip": p_s_prior,
    }


def autotune_all_concepts(*, since_days: int = 30, write: bool = False) -> list[dict]:
    """Run autotune for every concept that has recent attempts.

    With ``write=False`` (default) returns the proposed tuning without
    touching the DB — used for shadow comparison. With ``write=True`` the
    new params are pushed into MasteryState rows.
    """
    from datetime import timedelta

    from curriculum.models import Concept
    from django.utils import timezone

    cutoff = timezone.now() - timedelta(days=since_days)
    results: list[dict] = []

    concept_ids = (
        TaskAttempt.objects
        .filter(created_at__gte=cutoff)
        .values_list("task__concept_id", flat=True)
        .distinct()
    )
    for concept_id in concept_ids:
        attempts = TaskAttempt.objects.filter(
            task__concept_id=concept_id,
            created_at__gte=cutoff,
        ).only("student_id", "is_correct")
        tuned = autotune_concept(concept_id, attempts)
        results.append(tuned)
        if write:
            MasteryState.objects.filter(concept_id=concept_id).update(
                p_guess=tuned["p_guess"],
                p_slip=tuned["p_slip"],
            )
    return results
