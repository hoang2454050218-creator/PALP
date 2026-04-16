import logging
import time
import uuid

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("palp")
perf_logger = logging.getLogger("palp.performance")

SLO_WARN_MS = 1000
SLO_ERROR_MS = 2000


class RequestIDMiddleware(MiddlewareMixin):
    """Attach a unique request_id to every request for correlation/tracing."""

    HEADER_IN = "HTTP_X_REQUEST_ID"
    HEADER_OUT = "X-Request-ID"

    def process_request(self, request):
        incoming = request.META.get(self.HEADER_IN, "")
        try:
            request_id = uuid.UUID(incoming)
        except (ValueError, AttributeError):
            request_id = uuid.uuid4()
        request.request_id = request_id

    def process_response(self, request, response):
        rid = getattr(request, "request_id", None)
        if rid:
            response[self.HEADER_OUT] = str(rid)
        return response


class RequestIDLogFilter(logging.Filter):
    """Inject request_id into log records via thread-local storage."""

    def filter(self, record):
        record.request_id = getattr(record, "request_id", "-")
        return True


_thread_local_rid = None


class RequestIDLoggingMiddleware(MiddlewareMixin):
    """Push request_id into thread-local for the log filter."""

    def process_request(self, request):
        global _thread_local_rid
        _thread_local_rid = getattr(request, "request_id", None)

    def process_response(self, request, response):
        global _thread_local_rid
        _thread_local_rid = None
        return response


class RequestTimingMiddleware(MiddlewareMixin):
    """Track request duration, set X-Response-Time header, log SLO breaches."""

    def process_request(self, request):
        request._start_time = time.monotonic()

    def process_response(self, request, response):
        start = getattr(request, "_start_time", None)
        if start is None:
            return response

        duration_ms = (time.monotonic() - start) * 1000
        response["X-Response-Time-Ms"] = f"{duration_ms:.1f}"

        path = request.path
        method = request.method
        rid = getattr(request, "request_id", "-")

        if duration_ms >= SLO_ERROR_MS:
            perf_logger.error(
                "SLO breach: %s %s took %.1fms [rid=%s] (limit %dms)",
                method,
                path,
                duration_ms,
                rid,
                SLO_ERROR_MS,
                extra={
                    "duration_ms": duration_ms,
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "request_id": str(rid),
                    "slo_threshold_ms": SLO_ERROR_MS,
                },
            )
        elif duration_ms >= SLO_WARN_MS:
            perf_logger.warning(
                "Slow request: %s %s took %.1fms [rid=%s]",
                method,
                path,
                duration_ms,
                rid,
                extra={
                    "duration_ms": duration_ms,
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "request_id": str(rid),
                },
            )

        return response


class RequestMetricsMiddleware(MiddlewareMixin):
    """Increment per-status-class counters in Redis for error-rate SLO tracking.

    Keys: ``palp:http:<date>:2xx``, ``palp:http:<date>:5xx``, ``palp:http:<date>:total``
    """

    def process_response(self, request, response):
        try:
            from django.core.cache import cache
            from django.utils import timezone

            today = timezone.now().strftime("%Y-%m-%d")
            status_class = f"{response.status_code // 100}xx"
            cache.incr(f"palp:http:{today}:{status_class}")
            cache.incr(f"palp:http:{today}:total")
        except Exception:
            pass
        return response
