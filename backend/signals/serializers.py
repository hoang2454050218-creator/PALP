from rest_framework import serializers

from events.models import EventLog

from .services import ACCEPTED_EVENT_NAMES


class _SignalEventSerializer(serializers.Serializer):
    event_name = serializers.ChoiceField(choices=sorted(ACCEPTED_EVENT_NAMES))
    client_timestamp = serializers.DateTimeField()
    properties = serializers.JSONField(required=False, default=dict)
    idempotency_key = serializers.CharField(
        required=False, allow_blank=True, max_length=150,
    )


class SignalIngestSerializer(serializers.Serializer):
    raw_session_id = serializers.CharField(max_length=120)
    canonical_session_id = serializers.UUIDField(required=False, allow_null=True)
    events = _SignalEventSerializer(many=True, allow_empty=False)

    def validate_events(self, value):
        max_batch = 200
        if len(value) > max_batch:
            raise serializers.ValidationError(
                f"Batch too large; send <= {max_batch} events at a time."
            )
        return value


class SignalSessionSerializer(serializers.Serializer):
    """Read-only shape for /api/signals/my/."""

    canonical_session_id = serializers.UUIDField(allow_null=True)
    raw_session_id = serializers.CharField()
    window_start = serializers.DateTimeField()
    window_end = serializers.DateTimeField()
    focus_minutes = serializers.FloatField()
    idle_minutes = serializers.FloatField()
    tab_switches = serializers.IntegerField()
    hint_count = serializers.IntegerField()
    frustration_score = serializers.FloatField()
    give_up_count = serializers.IntegerField()
    response_time_outliers = serializers.IntegerField()
    struggle_count = serializers.IntegerField()
    raw_event_count = serializers.IntegerField()
    session_quality = serializers.FloatField()
