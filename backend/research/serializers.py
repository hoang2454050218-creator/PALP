from __future__ import annotations

from rest_framework import serializers

from .models import AnonymizedExport, ResearchParticipation, ResearchProtocol


class ResearchProtocolSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchProtocol
        fields = [
            "id", "code", "title", "description",
            "pi_name", "pi_email", "irb_number",
            "data_purposes", "data_categories",
            "retention_months", "status",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ResearchParticipationSerializer(serializers.ModelSerializer):
    protocol = ResearchProtocolSerializer(read_only=True)
    protocol_code = serializers.SlugRelatedField(
        source="protocol", queryset=ResearchProtocol.objects.all(),
        slug_field="code", write_only=True,
    )

    class Meta:
        model = ResearchParticipation
        fields = [
            "id", "protocol", "protocol_code",
            "state", "consent_text_version",
            "decided_at", "withdrawn_at", "notes",
        ]
        read_only_fields = [
            "id", "consent_text_version", "decided_at", "withdrawn_at",
        ]


class AnonymizedExportSerializer(serializers.ModelSerializer):
    protocol_code = serializers.CharField(source="protocol.code", read_only=True)

    class Meta:
        model = AnonymizedExport
        fields = [
            "id", "protocol_code", "dataset_key",
            "record_count", "participant_count",
            "k_anonymity_value", "k_anonymity_passed",
            "suppressed_columns", "notes", "created_at",
        ]
        read_only_fields = fields
