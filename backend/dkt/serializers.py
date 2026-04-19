from __future__ import annotations

from rest_framework import serializers

from dkt.models import DKTPrediction


class DKTPredictionSerializer(serializers.ModelSerializer):
    concept_name = serializers.CharField(source="concept.name", read_only=True)
    concept_code = serializers.CharField(source="concept.code", read_only=True)
    model_family = serializers.CharField(source="model_version.family", read_only=True)
    model_semver = serializers.CharField(source="model_version.semver", read_only=True)

    class Meta:
        model = DKTPrediction
        fields = [
            "id",
            "concept",
            "concept_name",
            "concept_code",
            "model_family",
            "model_semver",
            "p_correct_next",
            "confidence",
            "explanation",
            "sequence_length",
            "computed_at",
        ]
        read_only_fields = fields
