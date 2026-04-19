"""
Session-linking service.

Algorithm:

1. Frontend sends ``raw_session_id`` + ``raw_fingerprint`` + ``user_id``
   on first event of every page load.
2. ``register_device(...)`` upserts a ``DeviceFingerprint`` row using the
   monthly-salt hash; without consent the row is created but flagged so
   linking stays scoped to a single device.
3. ``link_session(...)`` finds an existing ``CanonicalSession`` for the
   user where the temporal gap (vs ``last_event_at``) is below
   ``LINK_PROXIMITY_SECONDS`` *and* the fingerprint matches an existing
   link (or the user has consent for fingerprint-based linking) — and if
   none exists, opens a new ``CanonicalSession``.
4. Returns ``CanonicalSession`` so the caller can stamp the
   ``canonical_session_id`` on every emitted event.

The whole module is dependency-free apart from Django ORM so tests
don't require Redis or Celery.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import (
    CanonicalSession,
    DeviceFingerprint,
    SessionLink,
    current_salt_month,
    hash_fingerprint,
)

logger = logging.getLogger("palp")

DEFAULT_LINK_PROXIMITY_SECONDS = 5 * 60  # 5 minutes


def _proximity_seconds() -> int:
    return int(
        getattr(settings, "PALP_DEVICE_SESSIONS", {}).get(
            "LINK_PROXIMITY_SECONDS", DEFAULT_LINK_PROXIMITY_SECONDS
        )
    )


@transaction.atomic
def register_device(
    *,
    user,
    raw_fingerprint: str,
    user_agent_family: str = "",
    consent_given: bool = False,
) -> DeviceFingerprint:
    """Upsert a ``DeviceFingerprint`` row for the user.

    Same fingerprint hashed on the same month is a no-op update of
    ``last_seen_at``; a new month starts a fresh row by design (salt
    rotation).
    """
    digest, month = hash_fingerprint(raw_fingerprint)
    obj, created = DeviceFingerprint.objects.get_or_create(
        user=user,
        device_hash=digest,
        salt_month=month,
        defaults={
            "user_agent_family": user_agent_family,
            "consent_given": consent_given,
        },
    )
    if not created:
        update_fields = ["last_seen_at"]
        obj.last_seen_at = timezone.now()
        if consent_given and not obj.consent_given:
            obj.consent_given = True
            update_fields.append("consent_given")
        if user_agent_family and obj.user_agent_family != user_agent_family:
            obj.user_agent_family = user_agent_family
            update_fields.append("user_agent_family")
        obj.save(update_fields=update_fields)
    return obj


@transaction.atomic
def link_session(
    *,
    user,
    raw_session_id: str,
    fingerprint: DeviceFingerprint | None = None,
    now=None,
) -> CanonicalSession:
    """Link ``raw_session_id`` to a ``CanonicalSession`` for the user.

    - If a ``SessionLink`` for this raw id already exists, return its
      canonical session (idempotent).
    - Otherwise look for a recent canonical session within proximity and
      reuse if either (a) the user has fingerprint consent and the
      fingerprint matches a previous link, or (b) the proximity window
      already contains links from the same fingerprint.
    - Otherwise open a new canonical session.
    """
    now = now or timezone.now()
    existing_link = SessionLink.objects.filter(raw_session_id=raw_session_id).select_related(
        "canonical_session"
    ).first()
    if existing_link is not None:
        existing_link.canonical_session.last_event_at = now
        existing_link.canonical_session.save(update_fields=["last_event_at"])
        return existing_link.canonical_session

    cutoff = now - timedelta(seconds=_proximity_seconds())
    candidate = (
        CanonicalSession.objects.filter(user=user, last_event_at__gte=cutoff)
        .order_by("-last_event_at")
        .first()
    )

    can_reuse = False
    if candidate is not None:
        if fingerprint is None:
            # Without fingerprint we still allow reuse for very recent activity
            # (the proximity window guarantees it's the same user-session).
            can_reuse = True
        elif fingerprint.consent_given:
            # Reuse if any recent link in the candidate used this fingerprint
            can_reuse = SessionLink.objects.filter(
                canonical_session=candidate, fingerprint=fingerprint
            ).exists() or not SessionLink.objects.filter(canonical_session=candidate).exists()
        else:
            # No consent -> only reuse if we previously linked this exact fingerprint
            # to that canonical session (e.g. same browser refresh).
            can_reuse = SessionLink.objects.filter(
                canonical_session=candidate, fingerprint=fingerprint
            ).exists()

    if candidate and can_reuse:
        canonical = candidate
        canonical.last_event_at = now
        canonical.save(update_fields=["last_event_at"])
    else:
        canonical = CanonicalSession.objects.create(
            user=user,
            started_at=now,
            last_event_at=now,
        )

    SessionLink.objects.create(
        raw_session_id=raw_session_id,
        canonical_session=canonical,
        fingerprint=fingerprint,
    )
    return canonical


def purge_expired_fingerprints(*, max_age_days: int = 30) -> int:
    """Delete fingerprint rows whose ``salt_month`` is older than the rotation window.

    Returns the count deleted. Run from a nightly Celery task.
    """
    threshold = timezone.now() - timedelta(days=max_age_days)
    threshold_month = threshold.strftime("%Y-%m")
    qs = DeviceFingerprint.objects.exclude(salt_month=current_salt_month()).filter(
        last_seen_at__lt=threshold
    )
    # Use string ordering: any salt_month <= threshold_month qualifies
    qs = qs.filter(salt_month__lte=threshold_month)
    count, _ = qs.delete()
    if count:
        logger.info("Purged %d expired device fingerprints", count)
    return count
