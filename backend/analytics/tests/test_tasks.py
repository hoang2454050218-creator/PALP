import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.cache import cache

from analytics.constants import (
    CELERY_HEALTH_PING_CACHE_KEY,
    CELERY_HEALTH_PING_STALE_THRESHOLD_SECONDS,
)
from analytics.models import PilotReport
from analytics.tasks import (
    celery_health_ping,
    check_queue_backlog,
    generate_weekly_report,
    run_nightly_early_warnings,
    update_backup_age_metric,
    weekly_restore_drill,
)

pytestmark = pytest.mark.django_db


class TestRunNightlyEarlyWarnings:
    def test_runs_for_all_classes_returns_count(self, class_with_members):
        result = run_nightly_early_warnings()
        assert isinstance(result, int)

    def test_returns_zero_when_no_alerts_needed(self, student_class):
        result = run_nightly_early_warnings()
        assert result == 0


class TestGenerateWeeklyReport:
    def test_single_class_returns_report_id(self, class_with_members):
        result = generate_weekly_report(
            class_id=class_with_members.id, week_number=1,
        )

        assert isinstance(result, int)
        assert PilotReport.objects.filter(id=result).exists()

    def test_all_classes_returns_id_list(self, class_with_members):
        result = generate_weekly_report(class_id=None, week_number=1)

        assert isinstance(result, list)
        assert len(result) >= 1
        for report_id in result:
            assert PilotReport.objects.filter(id=report_id).exists()


class TestCeleryHealthPing:
    def setup_method(self):
        cache.delete(CELERY_HEALTH_PING_CACHE_KEY)

    def test_writes_unix_timestamp_to_cache(self):
        before = time.time()
        result = celery_health_ping()
        after = time.time()

        cached = cache.get(CELERY_HEALTH_PING_CACHE_KEY)
        assert cached is not None
        assert before <= float(cached) <= after
        assert before <= result["timestamp"] <= after

    def test_consecutive_pings_overwrite_with_latest_timestamp(self):
        celery_health_ping()
        first = float(cache.get(CELERY_HEALTH_PING_CACHE_KEY))
        time.sleep(0.01)
        celery_health_ping()
        second = float(cache.get(CELERY_HEALTH_PING_CACHE_KEY))

        assert second > first

    def test_health_check_recognises_recent_ping_as_healthy(self):
        from analytics.health import _check_celery_beat

        celery_health_ping()
        result = _check_celery_beat()
        assert result["status"] == "healthy"
        assert result["last_heartbeat_seconds_ago"] < CELERY_HEALTH_PING_STALE_THRESHOLD_SECONDS

    def test_health_check_reports_unknown_when_no_ping(self):
        from analytics.health import _check_celery_beat

        result = _check_celery_beat()
        assert result["status"] == "unknown"


class TestCheckQueueBacklog:
    def test_returns_skipped_when_redis_unavailable(self):
        with patch.dict("sys.modules", {"redis": None}):
            with patch("builtins.__import__", side_effect=ImportError("redis missing")):
                result = check_queue_backlog()
        assert result["status"] == "skipped"

    def test_returns_depths_for_each_queue(self):
        fake_client = type("FakeRedis", (), {"llen": lambda self, q: 7})()
        with patch("redis.from_url", return_value=fake_client):
            result = check_queue_backlog()

        assert result["status"] == "ok"
        assert "celery" in result["depths"]
        assert result["depths"]["celery"] == 7

    def test_handles_broker_connection_error_gracefully(self):
        with patch("redis.from_url", side_effect=ConnectionError("broker down")):
            result = check_queue_backlog()
        assert result["status"] == "error"
        assert "broker down" in result["error"]


class TestUpdateBackupAgeMetric:
    def test_returns_missing_when_no_sentinel(self, tmp_path, settings):
        settings.PALP_BACKUP_DIR = str(tmp_path)
        result = update_backup_age_metric()
        assert result["status"] == "missing"

    def test_computes_positive_age_for_recent_sentinel(self, tmp_path, settings):
        settings.PALP_BACKUP_DIR = str(tmp_path)
        sentinel = tmp_path / ".last_backup_unix"
        sentinel.write_text(str(time.time() - 3600))

        result = update_backup_age_metric()
        assert result["status"] == "ok"
        assert 3500 < result["age_seconds"] < 3700

    def test_handles_corrupt_sentinel_gracefully(self, tmp_path, settings):
        settings.PALP_BACKUP_DIR = str(tmp_path)
        (tmp_path / ".last_backup_unix").write_text("not-a-number")
        result = update_backup_age_metric()
        assert result["status"] == "error"


class TestWeeklyRestoreDrill:
    def test_skipped_when_no_metadata(self, tmp_path, settings):
        settings.PALP_BACKUP_DIR = str(tmp_path)
        result = weekly_restore_drill()
        assert result["status"] == "skipped"
        assert result["reason"] == "no_backup_metadata"

    def test_returns_error_when_artifact_missing(self, tmp_path, settings):
        settings.PALP_BACKUP_DIR = str(tmp_path)
        meta = {
            "timestamp_unix": time.time(),
            "artifact": "palp_x.sql.gz",
            "artifact_path": str(tmp_path / "palp_x.sql.gz"),
            "encrypted": False,
        }
        (tmp_path / ".last_backup_meta.json").write_text(json.dumps(meta))
        result = weekly_restore_drill()
        assert result["status"] == "error"
        assert result["reason"] == "artifact_missing"

    def test_skipped_when_encrypted_but_no_passphrase(
        self, tmp_path, settings, monkeypatch,
    ):
        settings.PALP_BACKUP_DIR = str(tmp_path)
        artifact = tmp_path / "palp_x.sql.gz.gpg"
        artifact.write_bytes(b"fake-encrypted")
        meta = {
            "timestamp_unix": time.time(),
            "artifact": artifact.name,
            "artifact_path": str(artifact),
            "encrypted": True,
        }
        (tmp_path / ".last_backup_meta.json").write_text(json.dumps(meta))
        monkeypatch.delenv("BACKUP_GPG_PASSPHRASE", raising=False)

        result = weekly_restore_drill()
        assert result["status"] == "skipped"
        assert result["reason"] == "missing_gpg_passphrase"
