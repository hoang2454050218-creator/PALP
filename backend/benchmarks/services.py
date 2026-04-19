"""DB-aware benchmark orchestration.

Each public function is small + side-effecty in exactly one place
(``run_benchmark``) so callers (admin views, management commands,
later a Celery beat) all share the same persistence path.
"""
from __future__ import annotations

import importlib
import logging
from typing import Iterable, Mapping, Sequence

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .evaluator import PREDICTORS, evaluate
from .loaders import Attempt
from .models import BenchmarkDataset, BenchmarkResult, BenchmarkRun

logger = logging.getLogger("palp.benchmarks")


def list_predictors() -> Sequence[str]:
    return tuple(PREDICTORS.keys())


def _resolve_loader(loader_path: str):
    if not loader_path:
        return None
    module_name, _, attr = loader_path.rpartition(".")
    if not module_name:
        return None
    module = importlib.import_module(module_name)
    return getattr(module, attr, None)


def _loader_for(dataset: BenchmarkDataset):
    """Resolve the loader for a dataset.

    Order:
      1. Explicit ``dataset.loader_path`` (DB-driven override).
      2. ``settings.PALP_BENCHMARKS["LOADERS"][source]``.
      3. None (caller raises).
    """
    loader = _resolve_loader(dataset.loader_path)
    if loader is not None:
        return loader
    cfg = getattr(settings, "PALP_BENCHMARKS", {}) or {}
    loaders: Mapping[str, str] = cfg.get("LOADERS", {})
    return _resolve_loader(loaders.get(dataset.source, ""))


def ensure_default_datasets() -> list[BenchmarkDataset]:
    """Idempotently seed the two default benchmarks rows."""
    defaults = [
        {
            "key": "ednet-kt1-synth",
            "title": "EdNet-KT1 (synthetic stand-in)",
            "source": BenchmarkDataset.Source.EDNET,
            "description": (
                "Deterministic IRT-shaped synthetic data following the "
                "EdNet-KT1 distributional skew (long sequences, modest "
                "concept set). Replace with real EdNet CSV in production."
            ),
            "license": "synthetic",
            "loader_path": "benchmarks.loaders.ednet_synthetic",
        },
        {
            "key": "assistments-2009-synth",
            "title": "ASSISTments 2009 (synthetic stand-in)",
            "source": BenchmarkDataset.Source.ASSISTMENTS_2009,
            "description": (
                "Deterministic IRT-shaped synthetic data following the "
                "ASSISTments 2009-2010 shape (more concepts, shorter "
                "sequences). Replace with real ASSISTments CSV in "
                "production."
            ),
            "license": "synthetic",
            "loader_path": "benchmarks.loaders.assistments_2009_synthetic",
        },
    ]
    out: list[BenchmarkDataset] = []
    for spec in defaults:
        ds, _ = BenchmarkDataset.objects.get_or_create(
            key=spec["key"], defaults=spec,
        )
        out.append(ds)
    return out


@transaction.atomic
def run_benchmark(
    dataset: BenchmarkDataset,
    *,
    predictor: str,
    seed: int | None = None,
    sample_size: int | None = None,
    requested_by=None,
    notes: str = "",
) -> BenchmarkRun:
    """Execute one (dataset × predictor) run and persist results.

    Always returns the ``BenchmarkRun`` row, even on failure — the
    ``status`` field tells the caller whether it succeeded. We deliberately
    do not bubble exceptions out (this is meant to drive a UI / admin
    panel) but we DO log them with traceback for debugging. The
    only exception we DO raise is ``ValueError`` for an unknown
    predictor key, which is a programming error, not a runtime one.
    """
    if predictor not in PREDICTORS:
        raise ValueError(
            f"Unknown predictor '{predictor}'. Known: {sorted(PREDICTORS)}"
        )
    cfg = getattr(settings, "PALP_BENCHMARKS", {}) or {}
    seed = int(seed if seed is not None else cfg.get("DEFAULT_SEED", 42))
    sample_size = int(sample_size or cfg.get("DEFAULT_SAMPLE_SIZE", 200))

    run = BenchmarkRun.objects.create(
        dataset=dataset,
        model_label=predictor,
        model_family=predictor.split("_")[0],
        seed=seed,
        sample_size=sample_size,
        hyperparameters={
            "train_ratio": 0.8,
            "predictor": predictor,
        },
        notes=notes or "",
        status=BenchmarkRun.Status.RUNNING,
        requested_by=requested_by,
    )

    try:
        loader = _loader_for(dataset)
        if loader is None:
            raise RuntimeError(
                f"No loader resolved for dataset '{dataset.key}' "
                f"(source='{dataset.source}')."
            )
        attempts: Iterable[Attempt] = loader(seed=seed) if loader.__code__.co_argcount else loader()
        attempts = list(attempts)[: sample_size or None]
        result = evaluate(attempts, predictor=predictor)

        BenchmarkResult.objects.bulk_create([
            BenchmarkResult(run=run, metric_key=k, value=float(v))
            for k, v in result.metrics.items()
        ])

        run.status = (
            BenchmarkRun.Status.SUCCESS if result.metrics
            else BenchmarkRun.Status.FAILED
        )
        run.finished_at = timezone.now()
        if not result.metrics:
            run.notes = (
                (run.notes + "\n").strip()
                + f"Predictor '{predictor}' opted out (no engine available)."
            )
        run.save(update_fields=["status", "finished_at", "notes"])

        ds_updates: dict[str, int] = {}
        if attempts:
            ds_updates = {
                "students": len({a.student_id for a in attempts}),
                "concepts": len({a.concept_id for a in attempts}),
                "interactions": len(attempts),
            }
            for k, v in ds_updates.items():
                setattr(dataset, k, max(getattr(dataset, k), v))
            dataset.save(update_fields=list(ds_updates.keys()))

    except Exception as exc:
        logger.exception("Benchmark run %s failed", run.id)
        run.status = BenchmarkRun.Status.FAILED
        run.notes = (run.notes + f"\nERROR: {exc}").strip()
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "notes", "finished_at"])

    return run


def list_runs(dataset_key: str | None = None, *, limit: int = 50) -> Sequence[BenchmarkRun]:
    qs = BenchmarkRun.objects.select_related("dataset").order_by("-started_at")
    if dataset_key:
        qs = qs.filter(dataset__key=dataset_key)
    return list(qs[:limit])
