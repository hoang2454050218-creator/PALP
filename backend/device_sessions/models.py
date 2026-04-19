"""
Device fingerprint + canonical session linking.

A student typically uses laptop + mobile within the same week. Without
stitching, every device looks like a different "session" and BKT / risk
score / signal aggregates split the user into mini-personas. This app
keeps a stable hashed fingerprint per device and groups raw session ids
into a ``canonical_session_id`` so downstream consumers can join across
devices without exposing the underlying raw fingerprint.

Privacy invariants (enforced by the linker service + DPIA):

* Raw fingerprint never leaves the database.
* The ``canonical_session_id`` is opaque and stable per user-week.
* Linking requires the user's ``device_fingerprinting`` consent;
  unconsented sessions still get a canonical id but are scoped to the
  single device that produced them.
* Hash includes a per-month rotated salt so devices anonymise themselves
  after a 30-day retention window.
"""
import hashlib
import secrets
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class DeviceFingerprint(models.Model):
    """One row per (user, device_hash) pair.

    ``device_hash`` is computed client-side from canvas + audio + UA
    fingerprint and salted server-side with the current monthly salt
    before being stored. The plaintext fingerprint never touches the DB.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="device_fingerprints",
    )
    device_hash = models.CharField(
        max_length=64,
        help_text="SHA-256 of (raw fingerprint + monthly salt). Rotates monthly.",
    )
    salt_month = models.CharField(
        max_length=7,
        help_text="YYYY-MM marker for the salt epoch used when hashing.",
    )
    user_agent_family = models.CharField(
        max_length=80, blank=True,
        help_text="Coarse UA family (e.g. 'chrome-windows'), no version detail.",
    )
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(default=timezone.now)
    consent_given = models.BooleanField(
        default=False,
        help_text="Snapshot of the user's device_fingerprinting consent at the time of registration.",
    )

    class Meta:
        db_table = "palp_device_fingerprint"
        ordering = ["-last_seen_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "device_hash", "salt_month"],
                name="uq_device_fingerprint_user_hash_month",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "-last_seen_at"]),
            models.Index(fields=["device_hash", "salt_month"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.device_hash[:8]}…"


class CanonicalSession(models.Model):
    """Canonical session id grouping multiple device sessions for the same user.

    Created by the linker. Down-stream consumers (signals, risk, dkt) join
    on ``canonical_session_id`` rather than the raw frontend session id.
    """

    canonical_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="canonical_sessions",
    )
    started_at = models.DateTimeField(default=timezone.now)
    last_event_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "palp_canonical_session"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["user", "-started_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.canonical_id}"


class SessionLink(models.Model):
    """Mapping from raw frontend session id to a CanonicalSession."""

    raw_session_id = models.CharField(max_length=120)
    canonical_session = models.ForeignKey(
        CanonicalSession,
        on_delete=models.CASCADE,
        related_name="links",
    )
    fingerprint = models.ForeignKey(
        DeviceFingerprint,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="session_links",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_session_link"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["raw_session_id"],
                name="uq_session_link_raw_id",
            ),
        ]
        indexes = [
            models.Index(fields=["canonical_session", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.raw_session_id} → {self.canonical_session.canonical_id}"


def current_salt_month() -> str:
    return timezone.now().strftime("%Y-%m")


def server_salt_for_month(month: str) -> str:
    """Return the server-side salt for a given YYYY-MM.

    Pulls from settings.SECRET_KEY + month so each month produces a
    fresh deterministic salt. After 30 days the underlying device cannot
    be re-derived from the stored hash, satisfying the DPIA retention
    requirement.
    """
    base = settings.SECRET_KEY or secrets.token_hex(32)
    return hashlib.sha256(f"{base}:{month}".encode("utf-8")).hexdigest()[:32]


def hash_fingerprint(raw_fingerprint: str, *, month: str | None = None) -> tuple[str, str]:
    """Hash a client-supplied fingerprint with the current monthly salt.

    Returns ``(device_hash, salt_month)``.
    """
    month = month or current_salt_month()
    salt = server_salt_for_month(month)
    digest = hashlib.sha256(f"{salt}:{raw_fingerprint}".encode("utf-8")).hexdigest()
    return digest, month
