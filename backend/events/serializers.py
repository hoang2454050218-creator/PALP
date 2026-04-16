import json

from rest_framework import serializers

from .models import EventLog

MAX_JSON_SIZE = 10_000


class SanitizedJSONField(serializers.JSONField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        raw = json.dumps(value) if not isinstance(value, str) else value
        if len(raw) > MAX_JSON_SIZE:
            raise serializers.ValidationError(
                f"JSON data exceeds maximum size of {MAX_JSON_SIZE} characters."
            )
        return value


class EventLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventLog
        fields = (
            "id",
            "event_name",
            "properties",
            "session_id",
            "device_type",
            "source_page",
            "timestamp_utc",
        )
        read_only_fields = ("id", "timestamp_utc")


class TrackEventSerializer(serializers.Serializer):
    event_name = serializers.ChoiceField(choices=EventLog.EventName.choices)
    properties = SanitizedJSONField(required=False, default=dict)
    session_id = serializers.CharField(required=False, allow_blank=True, default="", max_length=100)
    device_type = serializers.CharField(required=False, allow_blank=True, default="", max_length=30)
    device = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=50,
        write_only=True,
        help_text="Legacy alias for device_type; prefer device_type.",
    )
    source_page = serializers.CharField(required=False, allow_blank=True, default="", max_length=200)
    client_timestamp = serializers.DateTimeField(required=False, allow_null=True)
    idempotency_key = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, max_length=150
    )
    course_id = serializers.IntegerField(required=False, allow_null=True)
    class_id = serializers.IntegerField(required=False, allow_null=True)
    concept_id = serializers.IntegerField(required=False, allow_null=True)
    task_id = serializers.IntegerField(required=False, allow_null=True)
    difficulty_level = serializers.IntegerField(required=False, allow_null=True)
    attempt_number = serializers.IntegerField(required=False, allow_null=True)
    mastery_before = serializers.FloatField(required=False, allow_null=True)
    mastery_after = serializers.FloatField(required=False, allow_null=True)
    intervention_reason = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=100
    )

    def validate(self, attrs):
        if attrs.get("device") and not attrs.get("device_type"):
            attrs["device_type"] = (attrs.get("device") or "")[:30]
        attrs.pop("device", None)
        return attrs


class BatchTrackSerializer(serializers.Serializer):
    events = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        max_length=500,
    )

    def validate(self, attrs):
        for ev in attrs["events"]:
            ser = TrackEventSerializer(data=ev)
            ser.is_valid(raise_exception=True)
        return attrs
