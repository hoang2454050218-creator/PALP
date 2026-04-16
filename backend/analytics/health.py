import time
import logging

from django.conf import settings
from django.db import connection
from django.core.cache import cache
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger("palp.health")


def _check_db():
    try:
        start = time.monotonic()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        latency_ms = (time.monotonic() - start) * 1000
        return {"status": "healthy", "latency_ms": round(latency_ms, 2)}
    except Exception as exc:
        logger.error("DB health check failed: %s", exc)
        return {"status": "unhealthy", "error": str(exc)}


def _check_redis():
    try:
        start = time.monotonic()
        cache.set("_health_ping", "1", timeout=10)
        val = cache.get("_health_ping")
        latency_ms = (time.monotonic() - start) * 1000
        if val != "1":
            return {"status": "degraded", "latency_ms": round(latency_ms, 2)}
        return {"status": "healthy", "latency_ms": round(latency_ms, 2)}
    except Exception as exc:
        logger.error("Redis health check failed: %s", exc)
        return {"status": "unhealthy", "error": str(exc)}


def _check_celery():
    try:
        from palp.celery import app as celery_app

        inspector = celery_app.control.inspect(timeout=3)
        active = inspector.active()
        if active is None:
            return {"status": "unhealthy", "error": "no workers responding"}
        worker_count = len(active)
        return {"status": "healthy", "workers": worker_count}
    except Exception as exc:
        logger.error("Celery health check failed: %s", exc)
        return {"status": "unhealthy", "error": str(exc)}


def _check_celery_beat():
    try:
        last_ping = cache.get("palp:celery:health_ping")
        if last_ping is None:
            return {"status": "unknown", "detail": "no heartbeat recorded yet"}
        elapsed = time.time() - float(last_ping)
        if elapsed > 600:
            return {"status": "unhealthy", "last_heartbeat_seconds_ago": round(elapsed)}
        return {"status": "healthy", "last_heartbeat_seconds_ago": round(elapsed)}
    except Exception as exc:
        logger.error("Celery Beat health check failed: %s", exc)
        return {"status": "unhealthy", "error": str(exc)}


def _check_queue_depth():
    try:
        import redis as redis_lib

        broker_url = getattr(settings, "CELERY_BROKER_URL", "redis://localhost:6379/1")
        r = redis_lib.from_url(broker_url)
        depth = r.llen("celery")
        thresholds = getattr(settings, "PALP_QUEUE_ALERT", {})
        warn_threshold = thresholds.get("WARN", 50)
        critical_threshold = thresholds.get("CRITICAL", 200)

        if depth >= critical_threshold:
            level = "critical"
            logger.error("Queue backlog critical: %d tasks pending", depth)
        elif depth >= warn_threshold:
            level = "warning"
            logger.warning("Queue backlog elevated: %d tasks pending", depth)
        else:
            level = "normal"

        return {"status": level, "depth": depth}
    except Exception as exc:
        logger.error("Queue depth check failed: %s", exc)
        return {"status": "unknown", "error": str(exc)}


def _compute_error_rate():
    try:
        from django.utils import timezone

        today = timezone.now().strftime("%Y-%m-%d")
        total = cache.get(f"palp:http:{today}:total")
        errors_5xx = cache.get(f"palp:http:{today}:5xx")

        if not total:
            return {"status": "ok", "detail": "no data yet today"}

        total = int(total)
        errors_5xx = int(errors_5xx or 0)
        rate = (errors_5xx / total) * 100 if total > 0 else 0

        slo_limit = getattr(settings, "PALP_SLO", {}).get("ERROR_RATE_PERCENT", 0.5)
        return {
            "status": "breach" if rate > slo_limit else "ok",
            "rate_percent": round(rate, 3),
            "total_requests": total,
            "total_5xx": errors_5xx,
            "slo_limit_percent": slo_limit,
        }
    except Exception:
        return {"status": "unknown"}


class LivenessView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def get(self, request):
        return Response({"status": "ok"})


class ReadinessView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def get(self, request):
        db = _check_db()
        redis = _check_redis()

        components = {"database": db, "cache": redis}
        all_healthy = all(c["status"] == "healthy" for c in components.values())

        return Response(
            {
                "status": "ready" if all_healthy else "degraded",
                "components": components,
            },
            status=status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class DeepHealthView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request):
        db = _check_db()
        redis = _check_redis()
        celery = _check_celery()
        beat = _check_celery_beat()
        queue = _check_queue_depth()
        error_rate = _compute_error_rate()

        components = {
            "database": db,
            "cache": redis,
            "celery_worker": celery,
            "celery_beat": beat,
            "queue": queue,
            "error_rate": error_rate,
        }

        unhealthy = [
            name for name, info in components.items()
            if info.get("status") in ("unhealthy", "critical", "breach")
        ]

        slo = getattr(settings, "PALP_SLO", {})

        return Response(
            {
                "status": "healthy" if not unhealthy else "unhealthy",
                "unhealthy_components": unhealthy,
                "components": components,
                "slo_targets": slo,
            },
            status=status.HTTP_200_OK if not unhealthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        )
