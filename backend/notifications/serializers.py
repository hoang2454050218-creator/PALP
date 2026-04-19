"""Serializers for the Notifications app."""
from __future__ import annotations

from rest_framework import serializers

from notifications.models import Notification, NotificationPreference


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            "in_app_enabled",
            "email_enabled",
            "push_enabled",
            "quiet_hours_start",
            "quiet_hours_end",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "channel",
            "severity",
            "category",
            "title",
            "body",
            "deep_link",
            "payload",
            "created_at",
            "read_at",
            "delivered_at",
        ]
        read_only_fields = fields
