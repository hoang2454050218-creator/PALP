"""
Pre-release clustering audit.

Used by the PeerEngine herd-cluster detector and any k-means/DBSCAN call
that affects student grouping. Fails when a cluster contains a
disproportionate concentration of one demographic value relative to the
population baseline.
"""
from __future__ import annotations

from typing import Callable, Iterable

from django.conf import settings

from .metrics import concentration_ratio
from .models import FairnessAudit


def audit_clustering(
    *,
    target_name: str,
    cluster_members: Iterable,
    total_population: Iterable,
    attribute_getters: dict[str, Callable],
    reviewed_by=None,
    notes: str = "",
) -> FairnessAudit:
    """Run concentration check for each named attribute.

    ``attribute_getters`` maps attribute name -> callable that returns the
    attribute value for a member object. Keeping it callable lets the
    caller decide whether to read from ``user.profile.gender``,
    ``user.demographic_band``, or anything else without coupling this
    module to the user model.
    """
    threshold_concentration = float(
        getattr(settings, "PALP_FAIRNESS", {}).get("CLUSTER_CONCENTRATION_MAX", 0.7)
    )
    min_baseline_for_violation = float(
        getattr(settings, "PALP_FAIRNESS", {}).get("CLUSTER_MIN_BASELINE", 0.5)
    )

    members_list = list(cluster_members)
    population_list = list(total_population)

    metrics: dict = {}
    violations: list[dict] = []

    for attr, getter in attribute_getters.items():
        result = concentration_ratio(members_list, population_list, getter)
        metrics[attr] = result

        for value, cluster_pct in result["cluster"].items():
            baseline_pct = result["baseline"].get(value, 0.0)
            # Violation if cluster over-concentrates a value that is NOT
            # already dominant in the population. ``<=`` so a 50/50 baseline
            # with a 90% cluster still trips the alarm.
            if cluster_pct > threshold_concentration and baseline_pct <= min_baseline_for_violation:
                violations.append({
                    "attr": attr,
                    "value": value,
                    "cluster_pct": cluster_pct,
                    "baseline_pct": baseline_pct,
                    "threshold": threshold_concentration,
                })

    audit = FairnessAudit.objects.create(
        target_name=target_name,
        kind=FairnessAudit.AuditKind.CLUSTERING,
        sensitive_attributes=list(attribute_getters.keys()),
        metrics=metrics,
        violations=violations,
        passed=not violations,
        sample_size=len(members_list),
        reviewed_by=reviewed_by,
        notes=notes,
    )
    return audit
