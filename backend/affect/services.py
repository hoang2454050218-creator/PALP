"""Affect ingestion + recall services.

Two write paths and one read path. The fusion path takes both a
keystroke and a linguistic estimate from the same observation
window and produces a single ``COMBINED`` snapshot — that is the
preferred input for the risk + bandit downstream consumers.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Iterable, Mapping

from django.conf import settings

from .engines import keystroke as keystroke_engine
from .engines import linguistic as linguistic_engine
from .models import AffectSnapshot


def _settings():
    return getattr(settings, "PALP_AFFECT", {}) or {}


def ingest_keystroke(student, payload: Mapping, *, duration_ms: int = 0) -> AffectSnapshot:
    cfg = _settings()
    snap = keystroke_engine.estimate(
        payload, min_sample=int(cfg.get("MIN_SAMPLE_KEYSTROKES", 10)),
    )
    return AffectSnapshot.objects.create(
        student=student,
        modality=AffectSnapshot.Modality.KEYSTROKE,
        valence=snap.valence,
        arousal=snap.arousal,
        confidence=snap.confidence,
        label=snap.label,
        features=snap.features,
        duration_ms=int(duration_ms or 0),
    )


def ingest_linguistic(
    student,
    text: str,
    *,
    language: str | None = None,
    duration_ms: int = 0,
) -> AffectSnapshot:
    cfg = _settings()
    snap = linguistic_engine.estimate(
        text,
        language=language or cfg.get("DEFAULT_LANG", "vi"),
        min_text_len=int(cfg.get("MIN_SAMPLE_TEXT_LEN", 8)),
    )
    return AffectSnapshot.objects.create(
        student=student,
        modality=AffectSnapshot.Modality.LINGUISTIC,
        valence=snap.valence,
        arousal=snap.arousal,
        confidence=snap.confidence,
        label=snap.label,
        features=snap.features,
        text_length=len(text or ""),
        duration_ms=int(duration_ms or 0),
    )


def fuse(
    student,
    *,
    keystroke_payload: Mapping | None = None,
    text: str | None = None,
    language: str | None = None,
    duration_ms: int = 0,
) -> AffectSnapshot:
    """Combine both modalities, weighted by per-engine confidence."""
    cfg = _settings()
    snaps: list[tuple[float, float, float, str, dict]] = []
    if keystroke_payload is not None:
        snap = keystroke_engine.estimate(
            keystroke_payload,
            min_sample=int(cfg.get("MIN_SAMPLE_KEYSTROKES", 10)),
        )
        snaps.append((snap.valence, snap.arousal, snap.confidence, snap.label, dict(snap.features)))
    if text:
        snap = linguistic_engine.estimate(
            text,
            language=language or cfg.get("DEFAULT_LANG", "vi"),
            min_text_len=int(cfg.get("MIN_SAMPLE_TEXT_LEN", 8)),
        )
        snaps.append((snap.valence, snap.arousal, snap.confidence, snap.label, dict(snap.features)))

    if not snaps:
        return AffectSnapshot.objects.create(
            student=student,
            modality=AffectSnapshot.Modality.COMBINED,
            valence=0.0,
            arousal=0.0,
            confidence=0.0,
            label="insufficient_sample",
            features={},
            text_length=len(text or ""),
            duration_ms=int(duration_ms or 0),
        )

    total_weight = sum(c for _, _, c, _, _ in snaps) or 1.0
    valence = sum(v * c for v, _, c, _, _ in snaps) / total_weight
    arousal = sum(a * c for _, a, c, _, _ in snaps) / total_weight
    confidence = min(1.0, total_weight / len(snaps))
    label = snaps[0][3] if len(snaps) == 1 else "combined"
    feature_blob = {
        "components": [
            {"label": s[3], "valence": s[0], "arousal": s[1], "confidence": s[2], "features": s[4]}
            for s in snaps
        ],
    }
    return AffectSnapshot.objects.create(
        student=student,
        modality=AffectSnapshot.Modality.COMBINED,
        valence=valence,
        arousal=arousal,
        confidence=confidence,
        label=label,
        features=feature_blob,
        text_length=len(text or ""),
        duration_ms=int(duration_ms or 0),
    )


def recent_for(student, *, limit: int = 20) -> Iterable[AffectSnapshot]:
    return AffectSnapshot.objects.filter(student=student)[:limit]
