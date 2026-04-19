"""Publication artefact authoring.

Two flows:

* **Auto-draft** — given a logical model in the MLOps registry,
  populate a Mitchell-style Model Card with the metadata we already
  have (description, intended use templated by model type, training
  data summary, latest published metrics, ethical considerations
  pulled from the model type's defaults).
* **Promote** — flip a draft into ``REVIEWED`` then ``PUBLISHED``;
  enforces that only one published row exists per model_label.

Datasheets follow the same pattern but key off
``benchmarks.BenchmarkDataset`` rows (or any other dataset_key the
caller provides).
"""
from __future__ import annotations

import logging
from typing import Mapping

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Datasheet, ModelCard, ReproducibilityKit

logger = logging.getLogger("palp.publication")


_MODEL_TYPE_TEMPLATES: dict[str, dict] = {
    "bkt": {
        "intended_use": (
            "Estimate per-concept mastery probability of a single "
            "learner from a sequence of (concept, correct?) attempts. "
            "Outputs feed PALP's adaptive pathway recommender."
        ),
        "out_of_scope_uses": [
            "High-stakes grading or pass/fail decisions.",
            "Cross-institution generalisation without re-fit.",
        ],
        "ethical": (
            "BKT estimates can be miscalibrated for learners with very "
            "few attempts. The pathway engine treats low-confidence "
            "estimates as 'unknown' rather than 'low mastery' to avoid "
            "self-fulfilling prophecies."
        ),
    },
    "dkt": {
        "intended_use": (
            "Sequence-aware probability that a learner answers the "
            "next attempted item correctly, conditional on their "
            "attempt history. Used as a secondary signal alongside BKT."
        ),
        "out_of_scope_uses": [
            "Punitive interventions; the model is sensitive to data drift.",
        ],
        "ethical": (
            "Pure-NumPy SAKT-style predictor with deterministic "
            "embeddings. Fairness audited via the ``fairness`` app on "
            "every release."
        ),
    },
    "risk_score": {
        "intended_use": (
            "Composite 0-100 risk score combining academic, "
            "behavioural, engagement, psychological, and metacognitive "
            "dimensions. Surfaced to lecturers in the dashboard."
        ),
        "out_of_scope_uses": [
            "Disciplinary decisions, financial-aid decisions, "
            "automatic class removal.",
        ],
        "ethical": (
            "Score is paired with SHAP-lite contributions and "
            "counterfactuals so lecturers see *why* a learner is "
            "flagged, never just a black-box number."
        ),
    },
    "bandit": {
        "intended_use": (
            "Online selection of nudge/intervention arms via Thompson "
            "sampling on Beta-Bernoulli posteriors."
        ),
        "out_of_scope_uses": ["Critical safety interventions."],
        "ethical": (
            "Bandit reward windows are short to limit exposure of any "
            "individual learner to a sub-optimal arm."
        ),
    },
}


def _settings() -> Mapping:
    return getattr(settings, "PALP_PUBLICATION", {}) or {}


def _intent_template(model_family: str) -> dict:
    return _MODEL_TYPE_TEMPLATES.get(
        model_family,
        {
            "intended_use": "See description.",
            "out_of_scope_uses": [],
            "ethical": "Pending — author should describe ethical scope.",
        },
    )


def draft_model_card(
    *,
    model_label: str,
    title: str | None = None,
    requested_by=None,
    registry_entry=None,
    benchmark_run=None,
) -> ModelCard:
    """Generate (or refresh) a draft Model Card.

    ``registry_entry`` and ``benchmark_run`` are accepted as opaque
    objects so this module does not import the MLOps / benchmarks app
    directly (avoiding a tight coupling cycle). Callers pass them in.
    """
    cfg = _settings()
    model_family = (model_label.split("@")[0].split("-")[0] or "").lower()
    template = _intent_template(model_family)

    training_data: dict = {}
    evaluation_data: dict = {}
    performance: dict = {}

    if registry_entry is not None:
        training_data["description"] = getattr(registry_entry, "description", "") or ""
        version = getattr(registry_entry, "production_version", None)
        if version is not None:
            performance.update(
                {
                    "metrics": getattr(version, "metrics_json", {}) or {},
                    "version": getattr(version, "semver", "n/a"),
                    "trained_at": (
                        getattr(version, "trained_at", None).isoformat()
                        if getattr(version, "trained_at", None) else None
                    ),
                }
            )

    if benchmark_run is not None:
        evaluation_data.update(
            {
                "benchmark_dataset": getattr(
                    getattr(benchmark_run, "dataset", None), "key", None,
                ),
                "predictor": getattr(benchmark_run, "model_label", None),
                "sample_size": getattr(benchmark_run, "sample_size", None),
            }
        )
        for r in getattr(benchmark_run, "results", []).all() if hasattr(benchmark_run, "results") else []:
            performance.setdefault("benchmark", {})[r.metric_key] = r.value

    with transaction.atomic():
        card, _created = ModelCard.objects.update_or_create(
            model_label=model_label,
            status=ModelCard.Status.DRAFT,
            defaults={
                "title": title or f"Model Card — {model_label}",
                "intended_use": template["intended_use"],
                "out_of_scope_uses": template["out_of_scope_uses"],
                "training_data": training_data,
                "evaluation_data": evaluation_data,
                "performance": performance,
                "ethical_considerations": template["ethical"],
                "caveats": (
                    "Draft generated automatically — review before "
                    "publishing for academic submission."
                ),
                "licence": cfg.get("LICENCE_DEFAULT", "CC-BY-4.0"),
                "authors": list(cfg.get("AUTHORS_DEFAULT", [])),
                "requested_by": requested_by,
            },
        )
    return card


def promote_model_card(card: ModelCard, *, target: str = "published") -> ModelCard:
    """Move a card forward through draft → reviewed → published.

    Refuses backwards transitions and enforces the (model_label,
    status='published') uniqueness by demoting any prior published
    row to ``reviewed``.
    """
    target = target.lower()
    if target not in {"reviewed", "published"}:
        raise ValueError("target must be 'reviewed' or 'published'")
    valid_progressions = {
        ("draft", "reviewed"),
        ("draft", "published"),
        ("reviewed", "published"),
    }
    if (card.status, target) not in valid_progressions:
        raise ValueError(
            f"Invalid promotion: {card.status} -> {target}"
        )
    with transaction.atomic():
        if target == "published":
            ModelCard.objects.filter(
                model_label=card.model_label,
                status=ModelCard.Status.PUBLISHED,
            ).exclude(pk=card.pk).update(status=ModelCard.Status.REVIEWED)
            card.status = ModelCard.Status.PUBLISHED
            card.published_at = timezone.now()
        else:
            card.status = ModelCard.Status.REVIEWED
        card.save(update_fields=["status", "published_at"])
    return card


def draft_datasheet(
    *,
    dataset_key: str,
    title: str | None = None,
    motivation: str = "",
    composition: dict | None = None,
    requested_by=None,
) -> Datasheet:
    cfg = _settings()
    sheet, _ = Datasheet.objects.update_or_create(
        dataset_key=dataset_key,
        status=Datasheet.Status.DRAFT,
        defaults={
            "title": title or f"Datasheet — {dataset_key}",
            "motivation": motivation or (
                "Why this dataset exists, who collected it, and the "
                "intended downstream tasks."
            ),
            "composition": composition or {},
            "uses": [],
            "licence": cfg.get("LICENCE_DEFAULT", "CC-BY-4.0"),
            "requested_by": requested_by,
        },
    )
    return sheet


def bundle_repro_kit(
    *,
    model_card: ModelCard,
    datasheet: Datasheet,
    benchmark_run_id: int | None = None,
    commit_hash: str = "",
    seed: int = 42,
    title: str | None = None,
    requested_by=None,
) -> ReproducibilityKit:
    return ReproducibilityKit.objects.create(
        title=title or f"Reproducibility kit for {model_card.model_label}",
        model_card=model_card,
        datasheet=datasheet,
        benchmark_run_id=benchmark_run_id,
        commit_hash=commit_hash,
        seed=seed,
        requested_by=requested_by,
    )
