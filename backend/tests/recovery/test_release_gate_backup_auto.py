"""Verify release_gate.check_ng07_backup auto-detects backup/restore freshness.

Wave 1 task: NG-07 / G-07 used to be MANUAL; the new sentinel-based check
should auto-PASS when both sentinels are recent and FAIL when stale.
"""
import sys
import time
from importlib import reload
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"

pytestmark = pytest.mark.recovery


@pytest.fixture
def release_gate(monkeypatch):
    """Import scripts/release_gate.py as a module (it uses sys.path tricks)."""
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        import release_gate as rg
        reload(rg)
        yield rg
    finally:
        sys.path.remove(str(SCRIPTS_DIR))


def _write_sentinel(path: Path, age_seconds: float):
    path.write_text(str(time.time() - age_seconds))


class TestNG07BackupAutoCheck:
    def test_manual_when_no_sentinels_present(self, release_gate, tmp_path, monkeypatch):
        monkeypatch.setenv("PALP_BACKUP_DIR", str(tmp_path))
        result = release_gate.check_ng07_backup()
        assert result.status == release_gate.Status.MANUAL

    def test_pass_when_both_sentinels_recent(self, release_gate, tmp_path, monkeypatch):
        monkeypatch.setenv("PALP_BACKUP_DIR", str(tmp_path))
        monkeypatch.setenv("PALP_BACKUP_MAX_AGE_HOURS", "26")
        monkeypatch.setenv("PALP_RESTORE_DRILL_MAX_AGE_DAYS", "14")
        _write_sentinel(tmp_path / ".last_backup_unix", 3600)
        _write_sentinel(tmp_path / ".last_restore_drill_unix", 86400)

        result = release_gate.check_ng07_backup()
        assert result.status == release_gate.Status.PASS
        assert "backup age" in result.detail

    def test_fail_when_backup_stale(self, release_gate, tmp_path, monkeypatch):
        monkeypatch.setenv("PALP_BACKUP_DIR", str(tmp_path))
        monkeypatch.setenv("PALP_BACKUP_MAX_AGE_HOURS", "26")
        monkeypatch.setenv("PALP_RESTORE_DRILL_MAX_AGE_DAYS", "14")
        _write_sentinel(tmp_path / ".last_backup_unix", 60 * 60 * 48)
        _write_sentinel(tmp_path / ".last_restore_drill_unix", 86400)

        result = release_gate.check_ng07_backup()
        assert result.status == release_gate.Status.FAIL
        assert "stale" in result.detail

    def test_fail_when_restore_drill_never_run(self, release_gate, tmp_path, monkeypatch):
        monkeypatch.setenv("PALP_BACKUP_DIR", str(tmp_path))
        _write_sentinel(tmp_path / ".last_backup_unix", 3600)

        result = release_gate.check_ng07_backup()
        assert result.status == release_gate.Status.FAIL
        assert "drill" in result.detail.lower()

    def test_fail_when_drill_stale(self, release_gate, tmp_path, monkeypatch):
        monkeypatch.setenv("PALP_BACKUP_DIR", str(tmp_path))
        monkeypatch.setenv("PALP_BACKUP_MAX_AGE_HOURS", "26")
        monkeypatch.setenv("PALP_RESTORE_DRILL_MAX_AGE_DAYS", "7")
        _write_sentinel(tmp_path / ".last_backup_unix", 3600)
        _write_sentinel(tmp_path / ".last_restore_drill_unix", 86400 * 30)

        result = release_gate.check_ng07_backup()
        assert result.status == release_gate.Status.FAIL
        assert "stale" in result.detail.lower()


class TestG07MirrorsNG07:
    def test_g07_uses_same_logic_as_ng07(self, release_gate, tmp_path, monkeypatch):
        monkeypatch.setenv("PALP_BACKUP_DIR", str(tmp_path))
        _write_sentinel(tmp_path / ".last_backup_unix", 3600)
        _write_sentinel(tmp_path / ".last_restore_drill_unix", 86400)

        ng = release_gate.check_ng07_backup()
        g = release_gate.check_g07_backup()
        assert ng.status == g.status
        assert g.check_id == "G-07"
