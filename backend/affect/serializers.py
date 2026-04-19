from __future__ import annotations

from rest_framework import serializers

from .models import AffectLexiconEntry, AffectSnapshot


class AffectSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AffectSnapshot
        fields = [
            "id", "modality", "valence", "arousal", "confidence",
            "label", "features", "text_length", "duration_ms",
            "occurred_at",
        ]
        read_only_fields = fields


class AffectLexiconSerializer(serializers.ModelSerializer):
    class Meta:
        model = AffectLexiconEntry
        fields = [
            "id", "term", "polarity", "valence_weight",
            "arousal_weight", "language", "notes",
        ]
        read_only_fields = ["id"]
