from rest_framework import serializers
from .models import WellbeingNudge


class WellbeingNudgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WellbeingNudge
        fields = ("id", "nudge_type", "response", "continuous_minutes", "created_at", "responded_at")
        read_only_fields = ("id", "created_at")


class CheckWellbeingSerializer(serializers.Serializer):
    continuous_minutes = serializers.IntegerField(min_value=0)


class NudgeResponseSerializer(serializers.Serializer):
    response = serializers.ChoiceField(choices=["accepted", "dismissed"])
