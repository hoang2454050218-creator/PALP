"""Multi-modal affect models — Phase 7 of v3 MAXIMAL.

Two non-camera-based affect signals (camera adds friction + privacy
load that we are not paying for):

* **Keystroke dynamics** — pause statistics + burst rate + backspace
  ratio. We only ingest *summary statistics*, never raw keystrokes,
  so there is no biometric template stored.
* **Linguistic affect** — short text the student types (reflection,
  goal, coach message). We tag with a small Vietnamese sentiment
  lexicon. No external NLP call.

Both surface as ``AffectSnapshot`` rows with valence/arousal scores
the risk + nudge engines can read.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models


class AffectSnapshot(models.Model):
    """One observation point.

    ``valence``: -1 (negative) → +1 (positive)
    ``arousal``:  0 (calm)     →  1 (highly aroused)
    ``confidence``: 0..1, drops when sample is short.
    """

    class Modality(models.TextChoices):
        KEYSTROKE = "keystroke", "Bàn phím"
        LINGUISTIC = "linguistic", "Ngôn ngữ"
        COMBINED = "combined", "Kết hợp"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="affect_snapshots",
    )
    modality = models.CharField(max_length=16, choices=Modality.choices)
    valence = models.FloatField(default=0.0)
    arousal = models.FloatField(default=0.0)
    confidence = models.FloatField(default=0.0)
    label = models.CharField(
        max_length=40, blank=True,
        help_text="Discrete label produced by the engine (engaged, frustrated, …).",
    )
    features = models.JSONField(
        default=dict, blank=True,
        help_text="Engine-specific feature values (sanitised, no raw text).",
    )
    text_length = models.PositiveIntegerField(default=0)
    duration_ms = models.PositiveIntegerField(default=0)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_affect_snapshot"
        indexes = [
            models.Index(fields=["student", "-occurred_at"]),
            models.Index(fields=["modality", "-occurred_at"]),
        ]
        ordering = ["-occurred_at"]

    def __str__(self) -> str:
        return (
            f"Affect({self.student_id}, {self.modality}, "
            f"v={self.valence:.2f}, a={self.arousal:.2f})"
        )


class AffectLexiconEntry(models.Model):
    """Small editable Vietnamese / English affect lexicon.

    We seed a baseline programmatically and let admins tune it.
    """

    class Polarity(models.TextChoices):
        POSITIVE = "positive", "Tích cực"
        NEGATIVE = "negative", "Tiêu cực"
        NEUTRAL = "neutral", "Trung tính"

    term = models.CharField(max_length=80, unique=True)
    polarity = models.CharField(max_length=16, choices=Polarity.choices)
    valence_weight = models.FloatField(default=0.0)
    arousal_weight = models.FloatField(default=0.0)
    language = models.CharField(max_length=8, default="vi")
    notes = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_affect_lexicon"
        ordering = ["term"]

    def __str__(self) -> str:
        return f"{self.term} ({self.polarity})"
