"""
Service layer over ``ModelRegistry`` / ``ModelVersion``.

Workflow:
1. ``register_model(name, type, owner)`` returns/creates a registry entry.
2. ``register_version(registry, semver, metrics, ...)`` records a training run.
3. ``promote(version, target_status, by)`` enforces the lifecycle:
   training -> shadow -> staging -> production -> deprecated -> archived.

Each promotion validates fairness + DP gates and writes ``promoted_at`` /
``promoted_by`` for audit.
"""
from __future__ import annotations

import logging
from typing import Iterable

from django.db import transaction

from .models import ModelRegistry, ModelVersion

logger = logging.getLogger("palp")


class PromotionError(ValueError):
    """Raised when a promotion violates the lifecycle invariants."""


_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    ModelVersion.Status.TRAINING: {ModelVersion.Status.SHADOW, ModelVersion.Status.STAGING, ModelVersion.Status.ARCHIVED},
    ModelVersion.Status.SHADOW: {ModelVersion.Status.STAGING, ModelVersion.Status.ARCHIVED},
    ModelVersion.Status.STAGING: {ModelVersion.Status.PRODUCTION, ModelVersion.Status.SHADOW, ModelVersion.Status.ARCHIVED},
    ModelVersion.Status.PRODUCTION: {ModelVersion.Status.DEPRECATED},
    ModelVersion.Status.DEPRECATED: {ModelVersion.Status.ARCHIVED, ModelVersion.Status.PRODUCTION},
    ModelVersion.Status.ARCHIVED: set(),
}


def register_model(
    name: str,
    model_type: str,
    *,
    owner=None,
    description: str = "",
) -> ModelRegistry:
    obj, created = ModelRegistry.objects.get_or_create(
        name=name,
        defaults={
            "model_type": model_type,
            "owner": owner,
            "description": description,
        },
    )
    if not created and obj.model_type != model_type:
        raise ValueError(
            f"Registry {name!r} already exists with type {obj.model_type!r}, "
            f"refusing to silently change to {model_type!r}."
        )
    return obj


def register_version(
    registry: ModelRegistry,
    semver: str,
    *,
    metrics: dict | None = None,
    params: dict | None = None,
    artifact_uri: str = "",
    training_data_ref: str = "",
    fairness_passed: bool = False,
    epsilon_dp: float | None = None,
    model_card_path: str = "",
    status: str = ModelVersion.Status.TRAINING,
) -> ModelVersion:
    """Record a new training run.

    Versions start in ``training`` status; explicit ``promote`` is required
    to ship them anywhere users can see them.
    """
    return ModelVersion.objects.create(
        registry=registry,
        semver=semver,
        status=status,
        artifact_uri=artifact_uri,
        metrics_json=metrics or {},
        params_json=params or {},
        training_data_ref=training_data_ref,
        fairness_passed=fairness_passed,
        epsilon_dp=epsilon_dp,
        model_card_path=model_card_path,
    )


@transaction.atomic
def promote(
    version: ModelVersion,
    target_status: str,
    *,
    by=None,
    bypass_gates: bool = False,
) -> ModelVersion:
    """Promote ``version`` to ``target_status`` enforcing the lifecycle.

    Production promotion additionally requires ``fairness_passed=True`` and,
    when the version was trained with DP, a finite ``epsilon_dp``. Set
    ``bypass_gates=True`` only from emergency rollback runbooks.
    """
    current = version.status
    allowed = _ALLOWED_TRANSITIONS.get(current, set())
    if target_status not in allowed:
        raise PromotionError(
            f"Cannot promote {version} from {current!r} to {target_status!r}. "
            f"Allowed transitions: {sorted(allowed)}."
        )

    if target_status == ModelVersion.Status.PRODUCTION and not bypass_gates:
        if not version.fairness_passed:
            raise PromotionError(
                f"Refusing to promote {version} to production: fairness gate not passed."
            )
        if version.epsilon_dp is not None and version.epsilon_dp <= 0:
            raise PromotionError(
                f"Refusing to promote {version} to production: epsilon_dp must be > 0 when set."
            )
        # Demote any other production version to deprecated
        ModelVersion.objects.filter(
            registry=version.registry,
            status=ModelVersion.Status.PRODUCTION,
        ).exclude(pk=version.pk).update(status=ModelVersion.Status.DEPRECATED)

    from django.utils import timezone

    version.status = target_status
    version.promoted_at = timezone.now()
    version.promoted_by = by
    version.save(update_fields=["status", "promoted_at", "promoted_by"])
    logger.info(
        "Promoted model version",
        extra={
            "model": version.registry.name,
            "semver": version.semver,
            "from_status": current,
            "to_status": target_status,
            "promoter": getattr(by, "username", "system"),
        },
    )
    return version


def production_versions() -> Iterable[ModelVersion]:
    return ModelVersion.objects.filter(
        status=ModelVersion.Status.PRODUCTION
    ).select_related("registry")
