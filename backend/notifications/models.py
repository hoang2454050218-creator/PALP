"""Notification models — Phase 4 of v3 MAXIMAL roadmap.

Lightweight in-app notifications. SSE / WebPush dispatchers will be
added later (Phase 4B); right now the API layer just persists rows
that the frontend polls. Because polling is fine at small scale (
< 1k students) and SSE/Push need infra (Redis pubsub, VAPID keys), we
intentionally skip them in this drop and keep the contract identical
so a future commit can add a real-time fanout without a migration.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models


class NotificationPreference(models.Model):
    """Per-user opt-in flags + quiet hours."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preference",
    )
    in_app_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=False)
    push_enabled = models.BooleanField(default=False)

    quiet_hours_start = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Local hour (0-23) when quiet hours start. Notifications still queued.",
    )
    quiet_hours_end = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Local hour (0-23) when quiet hours end.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "palp_notification_preference"

    def __str__(self) -> str:
        return f"NotifPref({self.user.username})"


class Notification(models.Model):
    """One in-app notification row."""

    class Channel(models.TextChoices):
        IN_APP = "in_app", "Trong ứng dụng"
        EMAIL = "email", "Email"
        PUSH = "push", "Push"

    class Severity(models.TextChoices):
        INFO = "info", "Thông tin"
        WARNING = "warning", "Cảnh báo"
        URGENT = "urgent", "Khẩn"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    channel = models.CharField(
        max_length=16, choices=Channel.choices, default=Channel.IN_APP,
    )
    severity = models.CharField(
        max_length=16, choices=Severity.choices, default=Severity.INFO,
    )

    category = models.CharField(
        max_length=40,
        help_text="Domain category, e.g. coach, emergency, peer, goals.",
    )
    title = models.CharField(max_length=160)
    body = models.TextField(blank=True)
    deep_link = models.CharField(max_length=255, blank=True)

    payload = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "palp_notification"
        indexes = [
            models.Index(fields=["user", "read_at", "-created_at"]),
            models.Index(fields=["category", "-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Notif({self.user.username}, {self.category}, {self.severity})"
