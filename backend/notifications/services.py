"""Notification dispatch service.

Today this just creates rows in the DB — the frontend polls
``GET /api/notifications/`` to fetch them. SSE / WebPush will replace
the polling in Phase 4B without changing this contract.
"""
from __future__ import annotations

from typing import Iterable

from django.utils import timezone

from notifications.models import Notification, NotificationPreference


def ensure_pref(user) -> NotificationPreference:
    pref, _ = NotificationPreference.objects.get_or_create(user=user)
    return pref


def dispatch(
    *,
    user,
    category: str,
    title: str,
    body: str = "",
    severity: str = Notification.Severity.INFO,
    deep_link: str = "",
    payload: dict | None = None,
    bypass_preference: bool = False,
) -> Notification | None:
    """Persist a notification (and respect user preferences unless overridden)."""
    pref = ensure_pref(user)
    if not bypass_preference and not pref.in_app_enabled:
        return None

    notif = Notification.objects.create(
        user=user,
        channel=Notification.Channel.IN_APP,
        severity=severity,
        category=category,
        title=title,
        body=body,
        deep_link=deep_link,
        payload=payload or {},
        delivered_at=timezone.now(),
    )
    return notif


def mark_read(*, user, ids: Iterable[int]) -> int:
    return (
        Notification.objects
        .filter(user=user, id__in=list(ids), read_at__isnull=True)
        .update(read_at=timezone.now())
    )


def unread_count(*, user) -> int:
    return Notification.objects.filter(user=user, read_at__isnull=True).count()
