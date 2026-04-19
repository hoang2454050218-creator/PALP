from datetime import timedelta

import pytest
from django.utils import timezone

from device_sessions.linker import (
    link_session,
    purge_expired_fingerprints,
    register_device,
)
from device_sessions.models import (
    CanonicalSession,
    DeviceFingerprint,
    SessionLink,
    hash_fingerprint,
)

pytestmark = pytest.mark.django_db


class TestRegisterDevice:
    def test_creates_fingerprint(self, student):
        fp = register_device(
            user=student,
            raw_fingerprint="canvas:abcd|audio:efgh|ua:chrome",
            user_agent_family="chrome-windows",
            consent_given=True,
        )
        assert DeviceFingerprint.objects.filter(pk=fp.pk).exists()
        assert fp.consent_given is True
        assert len(fp.device_hash) == 64

    def test_idempotent_same_month(self, student):
        a = register_device(user=student, raw_fingerprint="raw1")
        b = register_device(user=student, raw_fingerprint="raw1")
        assert a.pk == b.pk

    def test_different_fingerprints_create_distinct_rows(self, student):
        a = register_device(user=student, raw_fingerprint="raw1")
        b = register_device(user=student, raw_fingerprint="raw2")
        assert a.pk != b.pk
        assert a.device_hash != b.device_hash

    def test_consent_upgrade_persists(self, student):
        a = register_device(user=student, raw_fingerprint="raw1", consent_given=False)
        assert a.consent_given is False
        b = register_device(user=student, raw_fingerprint="raw1", consent_given=True)
        b.refresh_from_db()
        assert b.consent_given is True

    def test_hash_includes_monthly_salt(self):
        digest1, _ = hash_fingerprint("raw", month="2026-04")
        digest2, _ = hash_fingerprint("raw", month="2026-05")
        assert digest1 != digest2


class TestLinkSession:
    def test_creates_canonical_for_first_session(self, student):
        canonical = link_session(user=student, raw_session_id="rs-1")
        assert canonical.user == student
        assert SessionLink.objects.filter(raw_session_id="rs-1").exists()

    def test_idempotent_same_raw_id(self, student):
        a = link_session(user=student, raw_session_id="rs-1")
        b = link_session(user=student, raw_session_id="rs-1")
        assert a.canonical_id == b.canonical_id
        assert SessionLink.objects.filter(raw_session_id="rs-1").count() == 1

    def test_links_within_proximity_window(self, student):
        a = link_session(user=student, raw_session_id="rs-1")
        b = link_session(user=student, raw_session_id="rs-2")
        # Without fingerprint, recent activity gets stitched onto same canonical
        assert a.canonical_id == b.canonical_id

    def test_outside_proximity_creates_new_canonical(self, student):
        first = link_session(user=student, raw_session_id="rs-1")
        far_future = timezone.now() + timedelta(hours=2)
        second = link_session(user=student, raw_session_id="rs-2", now=far_future)
        assert first.canonical_id != second.canonical_id

    def test_fingerprint_with_consent_links_devices(self, student):
        fp = register_device(
            user=student, raw_fingerprint="raw-laptop", consent_given=True
        )
        a = link_session(user=student, raw_session_id="laptop-rs", fingerprint=fp)

        # New tab same browser within proximity -> same canonical
        b = link_session(user=student, raw_session_id="laptop-rs-2", fingerprint=fp)
        assert a.canonical_id == b.canonical_id

    def test_fingerprint_without_consent_only_links_same_device(self, student):
        fp_a = register_device(
            user=student, raw_fingerprint="device-a", consent_given=False
        )
        fp_b = register_device(
            user=student, raw_fingerprint="device-b", consent_given=False
        )
        a = link_session(user=student, raw_session_id="dev-a-1", fingerprint=fp_a)
        b = link_session(user=student, raw_session_id="dev-b-1", fingerprint=fp_b)
        # Without consent + different fingerprint -> separate canonical sessions
        assert a.canonical_id != b.canonical_id


class TestPurgeExpired:
    def test_removes_old_month_fingerprints(self, student):
        # Force an old fingerprint
        old = DeviceFingerprint.objects.create(
            user=student,
            device_hash="oldhash" + "0" * 56,
            salt_month="2025-01",
            last_seen_at=timezone.now() - timedelta(days=120),
        )
        recent_fp = register_device(user=student, raw_fingerprint="raw-current")
        deleted = purge_expired_fingerprints(max_age_days=30)
        assert deleted >= 1
        assert not DeviceFingerprint.objects.filter(pk=old.pk).exists()
        assert DeviceFingerprint.objects.filter(pk=recent_fp.pk).exists()

    def test_keeps_current_month(self, student):
        fp = register_device(user=student, raw_fingerprint="raw-current")
        purge_expired_fingerprints(max_age_days=0)
        # Even with max_age_days=0 we keep current month fingerprints
        assert DeviceFingerprint.objects.filter(pk=fp.pk).exists()
