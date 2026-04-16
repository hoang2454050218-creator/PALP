from rest_framework import serializers
from .models import ConsentRecord, AuditLog, PrivacyIncident, DataDeletionRequest
from .constants import CONSENT_PURPOSES, CONSENT_VERSION


class ConsentItemSerializer(serializers.Serializer):
    purpose = serializers.ChoiceField(choices=ConsentRecord.Purpose.choices)
    granted = serializers.BooleanField()


class GrantConsentSerializer(serializers.Serializer):
    consents = ConsentItemSerializer(many=True)
    version = serializers.CharField(default=CONSENT_VERSION)

    def validate_consents(self, value):
        purposes_seen = set()
        for item in value:
            if item["purpose"] in purposes_seen:
                raise serializers.ValidationError(
                    f"Duplicate purpose: {item['purpose']}"
                )
            purposes_seen.add(item["purpose"])
        return value


class ConsentStatusSerializer(serializers.Serializer):
    purpose = serializers.CharField()
    label = serializers.CharField()
    description = serializers.CharField()
    granted = serializers.BooleanField()
    last_changed_at = serializers.DateTimeField(allow_null=True)
    version = serializers.CharField(allow_null=True)


class ConsentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentRecord
        fields = (
            "id", "purpose", "granted", "version",
            "ip_address", "created_at",
        )
        read_only_fields = fields


class AuditLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(
        source="actor.username", read_only=True, default=None,
    )

    class Meta:
        model = AuditLog
        fields = (
            "id", "actor", "actor_username", "action",
            "target_user", "resource", "detail",
            "ip_address", "created_at",
        )
        read_only_fields = fields


class DataExportMetaSerializer(serializers.Serializer):
    exported_at = serializers.DateTimeField()
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    format_version = serializers.CharField()
    glossary = serializers.DictField()


class DataDeleteRequestSerializer(serializers.Serializer):
    tiers = serializers.ListField(
        child=serializers.ChoiceField(
            choices=["pii", "academic", "behavioral", "inference"]
        ),
        min_length=1,
    )
    confirm = serializers.BooleanField()

    def validate_confirm(self, value):
        if not value:
            raise serializers.ValidationError(
                "Bạn phải xác nhận (confirm=true) để tiếp tục xóa dữ liệu."
            )
        return value


class PrivacyIncidentSerializer(serializers.ModelSerializer):
    reporter_username = serializers.CharField(
        source="reported_by.username", read_only=True, default=None,
    )
    is_within_sla = serializers.BooleanField(read_only=True)

    class Meta:
        model = PrivacyIncident
        fields = (
            "id", "reported_by", "reporter_username", "severity",
            "status", "title", "description", "affected_user_count",
            "affected_data_tiers", "resolution", "resolved_at",
            "sla_deadline", "is_within_sla", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "reported_by", "reporter_username",
            "sla_deadline", "is_within_sla", "created_at", "updated_at",
        )


class PrivacyIncidentCreateSerializer(serializers.Serializer):
    severity = serializers.ChoiceField(choices=PrivacyIncident.Severity.choices)
    title = serializers.CharField(max_length=300)
    description = serializers.CharField()
    affected_user_count = serializers.IntegerField(min_value=0, default=0)
    affected_data_tiers = serializers.ListField(
        child=serializers.ChoiceField(
            choices=["pii", "academic", "behavioral", "inference"]
        ),
        default=list,
    )


class DeletionRequestStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataDeletionRequest
        fields = (
            "id", "tiers", "status", "result_summary",
            "requested_at", "completed_at",
        )
        read_only_fields = fields
