"""
Recovery test: Redis temporary loss.

Verifies that when Redis is temporarily unavailable:
  - BKT engine falls back to DB reads
  - Cache is repopulated on recovery
  - Dashboard overview degrades gracefully
  - Health endpoint reports 'degraded' status
"""
import pytest
from unittest.mock import patch, MagicMock

from django.core.cache import cache

from adaptive.engine import get_mastery_state, update_mastery
from adaptive.models import MasteryState
from analytics.health import _check_redis, _check_db

pytestmark = [pytest.mark.django_db, pytest.mark.recovery]


class TestMasteryDuringCacheOutage:
    """BKT operations must survive Redis being unreachable."""

    def test_get_mastery_falls_back_to_db(self, student, concepts):
        state = get_mastery_state(student.id, concepts[0].id)
        original_p = state.p_mastery

        with patch.object(cache, "get", side_effect=Exception("Redis down")):
            with patch.object(cache, "set", side_effect=Exception("Redis down")):
                db_state = get_mastery_state(student.id, concepts[0].id)
                assert db_state.pk == state.pk
                assert db_state.p_mastery == original_p

    def test_update_mastery_succeeds_without_cache(self, student, concepts):
        get_mastery_state(student.id, concepts[0].id)

        with patch.object(cache, "get", side_effect=Exception("Redis down")):
            with patch.object(cache, "set", side_effect=Exception("Redis down")):
                with patch.object(cache, "delete", side_effect=Exception("Redis down")):
                    updated = update_mastery(student.id, concepts[0].id, is_correct=True)
                    assert updated.attempt_count == 1

        db_state = MasteryState.objects.get(student=student, concept=concepts[0])
        assert db_state.attempt_count == 1

    def test_cache_repopulated_after_recovery(self, student, concepts):
        state = get_mastery_state(student.id, concepts[0].id)
        cache.clear()

        assert cache.get(f"mastery:{student.id}:{concepts[0].id}") is None

        recovered = get_mastery_state(student.id, concepts[0].id)
        assert recovered.pk == state.pk

        cached = cache.get(f"mastery:{student.id}:{concepts[0].id}")
        assert cached is not None
        assert cached.pk == state.pk


class TestDashboardDuringCacheOutage:
    """Dashboard must return data (slower) when cache is unavailable."""

    def test_overview_api_returns_without_cache(
        self, lecturer_api, class_with_members,
    ):
        cache.clear()
        resp = lecturer_api.get(
            f"/api/dashboard/class/{class_with_members.id}/overview/"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_students" in data

    def test_alerts_api_returns_without_cache(
        self, lecturer_api, class_with_members,
    ):
        cache.clear()
        resp = lecturer_api.get(
            f"/api/dashboard/alerts/?class_id={class_with_members.id}"
        )
        assert resp.status_code == 200


class TestHealthReportsDegradation:
    """Health endpoint must correctly report Redis degradation."""

    def test_redis_check_reports_unhealthy(self):
        with patch.object(
            cache, "set", side_effect=Exception("Connection refused")
        ):
            result = _check_redis()
            assert result["status"] in ("unhealthy", "degraded")

    def test_db_still_healthy_during_redis_outage(self):
        result = _check_db()
        assert result["status"] == "healthy"

    def test_readiness_endpoint_returns_503(self, anon_api):
        with patch(
            "analytics.health._check_redis",
            return_value={"status": "unhealthy", "error": "Connection refused"},
        ):
            resp = anon_api.get("/api/health/ready/")
            assert resp.status_code == 503
            assert resp.json()["status"] == "degraded"
