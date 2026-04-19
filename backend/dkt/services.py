"""DKT service layer — talk to the DB on behalf of the engine."""
from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from dkt.engine import (
    AttemptRecord,
    DKTHyper,
    DKTPredictionOutput,
    predict,
    predict_many,
)
from dkt.models import DKTAttemptLog, DKTModelVersion, DKTPrediction


CURRENT_MODEL_NAME = "sakt-numpy"
CURRENT_MODEL_SEMVER = "0.1.0"


@dataclass
class PredictResult:
    output: DKTPredictionOutput
    persisted: DKTPrediction


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_or_create_current_version() -> DKTModelVersion:
    """Return the in-use DKT model version, creating it if absent."""
    version, _ = DKTModelVersion.objects.get_or_create(
        name=CURRENT_MODEL_NAME,
        semver=CURRENT_MODEL_SEMVER,
        defaults={
            "family": "sakt-numpy",
            "status": DKTModelVersion.Status.PRODUCTION,
            "hyperparameters": DKTHyper().__dict__,
        },
    )
    return version


def history_for(student) -> list[AttemptRecord]:
    """Pull the student's attempt log in chronological order."""
    rows = (
        DKTAttemptLog.objects
        .filter(student=student)
        .order_by("occurred_at")
        .values("concept_id", "is_correct")
    )
    return [
        AttemptRecord(
            concept_id=int(r["concept_id"]),
            is_correct=bool(r["is_correct"]),
        )
        for r in rows
    ]


def all_concept_ids() -> list[int]:
    from curriculum.models import Concept
    return list(
        Concept.objects.filter(is_active=True).values_list("id", flat=True)
    )


@transaction.atomic
def predict_for_concept(*, student, target_concept_id: int) -> PredictResult:
    """Run the engine + persist a snapshot row."""
    version = get_or_create_current_version()
    history = history_for(student)
    concept_ids = all_concept_ids()
    output = predict(
        history=history,
        target_concept_id=target_concept_id,
        concept_ids=concept_ids,
        hyper=DKTHyper(**version.hyperparameters) if version.hyperparameters else None,
    )
    persisted, _ = DKTPrediction.objects.update_or_create(
        student=student,
        concept_id=target_concept_id,
        model_version=version,
        defaults={
            "p_correct_next": output.p_correct_next,
            "confidence": output.confidence,
            "explanation": {"attention": output.attention},
            "sequence_length": output.sequence_length,
        },
    )
    return PredictResult(output=output, persisted=persisted)


def predict_for_student(*, student, top_k: int | None = 10) -> list[PredictResult]:
    """Predict for every active concept; return the top-K weakest."""
    version = get_or_create_current_version()
    history = history_for(student)
    concept_ids = all_concept_ids()
    if not concept_ids:
        return []

    outputs = predict_many(
        history=history,
        target_concept_ids=concept_ids,
        concept_ids=concept_ids,
        hyper=DKTHyper(**version.hyperparameters) if version.hyperparameters else None,
    )

    results: list[PredictResult] = []
    with transaction.atomic():
        for cid, out in outputs.items():
            persisted, _ = DKTPrediction.objects.update_or_create(
                student=student,
                concept_id=cid,
                model_version=version,
                defaults={
                    "p_correct_next": out.p_correct_next,
                    "confidence": out.confidence,
                    "explanation": {"attention": out.attention},
                    "sequence_length": out.sequence_length,
                },
            )
            results.append(PredictResult(output=out, persisted=persisted))

    results.sort(key=lambda r: r.output.p_correct_next)  # weakest first
    if top_k is not None:
        return results[:top_k]
    return results


def import_attempt(
    *,
    student,
    concept,
    is_correct: bool,
    occurred_at=None,
    response_time_seconds: float | None = None,
    hint_count: int = 0,
    source_attempt_id: int | None = None,
) -> DKTAttemptLog:
    """Record one attempt the engine should consume."""
    return DKTAttemptLog.objects.create(
        student=student,
        concept=concept,
        is_correct=bool(is_correct),
        occurred_at=occurred_at or timezone.now(),
        response_time_seconds=response_time_seconds,
        hint_count=hint_count,
        source_attempt_id=source_attempt_id,
    )
