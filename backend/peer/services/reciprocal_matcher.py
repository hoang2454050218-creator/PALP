"""Reciprocal teaching matcher.

Goal: pair student A with student B such that **both** of these hold:

  * A is strong on concept X where B is weak (A teaches X to B)
  * B is strong on concept Y where A is weak (B teaches Y to A)

One-way tutoring is rejected on purpose — Topping (2005) and the
"protégé effect" (Fiorella & Mayer 2013) both depend on the student
being in the teaching role too. A pair without a credible reverse
direction is a worse outcome than no pair, so the matcher returns
``None`` rather than degrading to one-way tutoring.

Both candidates must already have ``peer_teaching`` consent and live
in the same active cohort. The matcher runs **inside** the cohort so
the teaching gap is in each other's ZPD (Vygotsky 1978) rather than
crossing ability bands.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from django.conf import settings
from django.db import transaction

logger = logging.getLogger("palp.peer.matcher")


@dataclass
class ConceptGap:
    concept_id: int
    teacher_mastery: float
    learner_mastery: float

    @property
    def gap(self) -> float:
        return self.teacher_mastery - self.learner_mastery


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_reciprocal_match(student) -> Optional["ReciprocalPeerMatch"]:
    """Find or return the best candidate for a reciprocal match.

    Returns ``None`` if no reciprocal pair exists. The caller decides
    whether to surface this to the user — typically the view returns
    a polite "no match yet, try again next week" message rather than
    treating absence as an error.
    """
    from peer.models import PeerCohort, ReciprocalPeerMatch
    from privacy.services import has_consent

    if not has_consent(student, "peer_teaching"):
        return None

    cohort = (
        PeerCohort.objects
        .filter(members=student, is_active=True)
        .order_by("-created_at")
        .first()
    )
    if not cohort:
        return None

    threshold = float(settings.PALP_PEER["BUDDY_STRONG_WEAK_THRESHOLD"])
    a_vec = _mastery_vector(student)
    if not a_vec:
        return None

    candidates = []
    for partner in cohort.members.exclude(id=student.id):
        if not has_consent(partner, "peer_teaching"):
            continue

        b_vec = _mastery_vector(partner)
        if not b_vec:
            continue

        a_to_b = _strong_weak_pairs(a_vec, b_vec, threshold=threshold)
        b_to_a = _strong_weak_pairs(b_vec, a_vec, threshold=threshold)

        if not a_to_b or not b_to_a:
            continue

        score = _compatibility_score(a_to_b, b_to_a)
        candidates.append((partner, score, a_to_b[0], b_to_a[0]))

    if not candidates:
        return None

    candidates.sort(key=lambda c: -c[1])
    partner, score, a_concept, b_concept = candidates[0]

    with transaction.atomic():
        match, created = ReciprocalPeerMatch.objects.get_or_create(
            cohort=cohort,
            student_a=student,
            student_b=partner,
            defaults={
                "concept_a_to_b_id": a_concept.concept_id,
                "concept_b_to_a_id": b_concept.concept_id,
                "compatibility_score": score,
                "status": ReciprocalPeerMatch.Status.PENDING,
            },
        )
        if not created:
            # Refresh the suggested concepts in case mastery changed.
            match.concept_a_to_b_id = a_concept.concept_id
            match.concept_b_to_a_id = b_concept.concept_id
            match.compatibility_score = score
            match.save(
                update_fields=[
                    "concept_a_to_b", "concept_b_to_a",
                    "compatibility_score", "updated_at",
                ]
            )

    return match


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mastery_vector(student) -> dict[int, float]:
    """Return ``{concept_id: p_mastery}`` for the student."""
    from adaptive.models import MasteryState
    return dict(
        MasteryState.objects
        .filter(student=student)
        .values_list("concept_id", "p_mastery")
    )


def _strong_weak_pairs(
    teacher_vec: dict[int, float],
    learner_vec: dict[int, float],
    *,
    threshold: float,
) -> list[ConceptGap]:
    """Return concept ids where ``teacher`` is strong and ``learner`` is weak.

    Strong-weak gap is filtered by ``threshold`` (default 0.30) so we
    don't propose teaching for marginal differences. Sorting by the
    gap puts the strongest reciprocity opportunities first.
    """
    gaps: list[ConceptGap] = []
    for concept_id, teacher_p in teacher_vec.items():
        learner_p = learner_vec.get(concept_id, 0.0)
        if teacher_p - learner_p >= threshold:
            gaps.append(
                ConceptGap(
                    concept_id=concept_id,
                    teacher_mastery=teacher_p,
                    learner_mastery=learner_p,
                )
            )
    gaps.sort(key=lambda g: -g.gap)
    return gaps


def _compatibility_score(a_to_b: list[ConceptGap], b_to_a: list[ConceptGap]) -> float:
    """Composite compatibility score for the matcher ranking.

    Heuristic:
        * Reward symmetry — pairs whose two best gaps are similar in
          size are more reciprocal than pairs where one direction is
          a tiny tutor + the other is a coach.
        * Reward absolute size — the two best gaps summed encourages
          the matcher to pick a pair with substantial mutual learning
          potential.
    """
    a = a_to_b[0].gap
    b = b_to_a[0].gap
    symmetry = 1.0 - abs(a - b) / max(a + b, 1e-9)
    return round((a + b) * (0.5 + 0.5 * symmetry), 4)
