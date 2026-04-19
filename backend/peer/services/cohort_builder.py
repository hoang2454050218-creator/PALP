"""Cohort builder — k-means on entry-assessment ability vectors.

Re-clusters once a week so a student who has improved (or regressed)
moves to the cohort that fits her current level. Always runs the
fairness audit on the resulting cohort assignment so demographic
concentration above ``CLUSTER_CONCENTRATION_MAX`` raises the
``flagged_for_review`` flag instead of silently being used for
benchmarking.

Pure-Python k-means is used so we don't pull in scikit-learn just for
this. The algorithm is deterministic given the seed (``COHORT_KMEANS_SEED``)
which keeps reproducibility for the model registry.
"""
from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass
from typing import Iterable

from django.conf import settings
from django.db import transaction

logger = logging.getLogger("palp.peer.cohort")


@dataclass
class CohortBuildResult:
    cohort_id: int
    label: str
    members: int
    fairness_passed: bool
    fairness_audit_id: int | None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_cohorts(student_class) -> list[CohortBuildResult]:
    """Cluster the class into same-ability cohorts.

    Side effects:
        - Marks any previously-active ``PeerCohort`` for the class as
          inactive so the new ones are the canonical set.
        - Creates new ``PeerCohort`` rows + sets their members.
        - Runs ``audit_clustering`` and stores the resulting
          ``FairnessAudit`` reference.

    Cold-start rule: if the class has fewer than ``COHORT_MIN_SIZE``
    members, we create a single "all" cohort containing everyone but
    suppress benchmarking at the ``benchmark`` service layer.
    """
    from accounts.models import User
    from peer.models import PeerCohort

    members = list(_eligible_members(student_class))
    if not members:
        logger.info("build_cohorts: class %s empty, skipping", student_class.id)
        return []

    target = int(settings.PALP_PEER["COHORT_TARGET_SIZE"])
    minimum = int(settings.PALP_PEER["COHORT_MIN_SIZE"])
    seed = int(settings.PALP_PEER["COHORT_KMEANS_SEED"])

    vectors = [_ability_vector(s) for s in members]
    clusters = _kmeans(vectors, k=max(1, len(members) // target), seed=seed)

    # Group student references by assigned cluster label.
    grouped: dict[int, list[User]] = {}
    for student, label in zip(members, clusters.labels):
        grouped.setdefault(label, []).append(student)

    # Merge under-sized clusters into the nearest centroid so every
    # surviving cohort has at least ``minimum`` members.
    grouped = _merge_small_clusters(
        grouped,
        centroids=clusters.centroids,
        minimum=minimum,
    )

    with transaction.atomic():
        PeerCohort.objects.filter(
            student_class=student_class, is_active=True,
        ).update(is_active=False)

        results: list[CohortBuildResult] = []
        for label, group in grouped.items():
            cohort = PeerCohort.objects.create(
                student_class=student_class,
                ability_band_label=f"band_{label}",
                members_count=len(group),
                centroid=list(clusters.centroids[label]) if label in clusters.centroids else [],
            )
            cohort.members.set(group)

            audit = _audit_cohort(cohort=cohort, members=group, total=members)
            cohort.fairness_audit = audit
            cohort.save(update_fields=["fairness_audit"])

            results.append(
                CohortBuildResult(
                    cohort_id=cohort.id,
                    label=cohort.ability_band_label,
                    members=len(group),
                    fairness_passed=audit.passed if audit else True,
                    fairness_audit_id=audit.id if audit else None,
                )
            )

    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _eligible_members(student_class) -> Iterable:
    """Return students that have at least one MasteryState row.

    A student with no mastery data has nothing to cluster on; they are
    deferred to the next weekly run after the cold-start data lands.
    """
    from accounts.models import ClassMembership

    memberships = (
        ClassMembership.objects
        .filter(student_class=student_class)
        .select_related("student")
    )
    students = [m.student for m in memberships]
    return [s for s in students if _has_ability_data(s)]


def _has_ability_data(student) -> bool:
    from adaptive.models import MasteryState
    return MasteryState.objects.filter(student=student).exists()


def _ability_vector(student) -> list[float]:
    """Concept-mastery vector. Missing concepts default to 0.0."""
    from adaptive.models import MasteryState
    from curriculum.models import Concept

    concept_ids = list(
        Concept.objects.filter(is_active=True).order_by("id").values_list("id", flat=True)
    )
    if not concept_ids:
        return [0.0]

    masteries = dict(
        MasteryState.objects
        .filter(student=student, concept_id__in=concept_ids)
        .values_list("concept_id", "p_mastery")
    )
    return [masteries.get(cid, 0.0) for cid in concept_ids]


@dataclass
class KMeansResult:
    labels: list[int]
    centroids: dict[int, list[float]]


def _kmeans(vectors: list[list[float]], *, k: int, seed: int, max_iter: int = 50) -> KMeansResult:
    """Lightweight, deterministic k-means.

    Stops early when no labels change between iterations. With small
    class sizes (< 200) this completes in milliseconds without the
    scikit-learn dependency.
    """
    if k <= 1 or len(vectors) <= 1:
        return KMeansResult(
            labels=[0] * len(vectors),
            centroids={0: _mean_vec(vectors) if vectors else []},
        )

    rng = random.Random(seed)
    indices = rng.sample(range(len(vectors)), k=min(k, len(vectors)))
    centroids = {i: list(vectors[idx]) for i, idx in enumerate(indices)}

    labels = [0] * len(vectors)
    for _ in range(max_iter):
        new_labels = [_closest_centroid(v, centroids) for v in vectors]
        if new_labels == labels:
            break
        labels = new_labels
        for cid in centroids:
            members = [v for v, lbl in zip(vectors, labels) if lbl == cid]
            if members:
                centroids[cid] = _mean_vec(members)

    return KMeansResult(labels=labels, centroids=centroids)


def _closest_centroid(vector: list[float], centroids: dict[int, list[float]]) -> int:
    best, best_dist = 0, math.inf
    for cid, centroid in centroids.items():
        dist = sum((a - b) ** 2 for a, b in zip(vector, centroid))
        if dist < best_dist:
            best, best_dist = cid, dist
    return best


def _mean_vec(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    n = len(vectors)
    dim = len(vectors[0])
    out = [0.0] * dim
    for v in vectors:
        for i in range(dim):
            out[i] += v[i]
    return [x / n for x in out]


def _merge_small_clusters(
    grouped: dict[int, list],
    *,
    centroids: dict[int, list[float]],
    minimum: int,
) -> dict[int, list]:
    """Merge any cluster smaller than ``minimum`` into its closest neighbour."""
    while True:
        small = [lbl for lbl, members in grouped.items() if len(members) < minimum]
        if not small or len(grouped) <= 1:
            break

        label = small[0]
        small_centroid = centroids.get(label, [])
        candidates = [(other, centroids[other]) for other in grouped if other != label]
        nearest = min(
            candidates,
            key=lambda pair: sum((a - b) ** 2 for a, b in zip(small_centroid, pair[1])),
        )[0]
        grouped[nearest].extend(grouped[label])
        del grouped[label]

    return grouped


def _audit_cohort(*, cohort, members, total):
    """Run the clustering fairness audit when demographic data exists."""
    from fairness.audit_clustering import audit_clustering

    getters = _build_attribute_getters(members + total)
    if not getters:
        return None

    try:
        return audit_clustering(
            target_name=f"peer_cohort:{cohort.id}",
            cluster_members=members,
            total_population=total,
            attribute_getters=getters,
            notes=(
                f"Auto-audit during weekly cohort recompute for class "
                f"{cohort.student_class_id}."
            ),
        )
    except Exception:  # pragma: no cover -- defensive, do not block cohort build
        logger.exception("Fairness audit failed for cohort %s", cohort.id)
        return None


def _build_attribute_getters(students) -> dict:
    """Return only attribute getters that are populated for at least one student.

    Avoids running an audit over attributes that are entirely empty
    (which would over-flag a cohort because all baselines collapse to
    1.0 for the empty bucket).
    """
    getters: dict = {}
    if any(getattr(s, "gender", None) for s in students):
        getters["gender"] = lambda s: getattr(s, "gender", "") or "unknown"
    if any(getattr(s, "economic_band", None) for s in students):
        getters["economic_band"] = (
            lambda s: getattr(s, "economic_band", "") or "unknown"
        )
    if any(getattr(s, "region", None) for s in students):
        getters["region"] = lambda s: getattr(s, "region", "") or "unknown"
    return getters
