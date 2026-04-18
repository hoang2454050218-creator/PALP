import contextvars
import logging
import time
import uuid

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("palp")
perf_logger = logging.getLogger("palp.performance")

SLO_WARN_MS = 1000
SLO_ERROR_MS = 2000

_request_id_ctx: contextvars.ContextVar = contextvars.ContextVar(
    "palp_request_id", default=None,
)


def get_current_request_id():
    """Return the request_id of the currently in-flight request, if any.

    Safe to call from any code path (views, signals, Celery tasks invoked
    from a request context) thanks to ContextVar isolation per-task/per-thread.
    """
    return _request_id_ctx.get()


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


class RequestIDLoggingMiddleware(MiddlewareMixin):
    """Bind request_id to a ContextVar so log records can pick it up.

    Uses contextvars instead of a module-level global so concurrent requests
    in WSGI thread workers (or asyncio handlers) cannot leak request ids
    into each other's log lines.
    """

    def process_request(self, request):
        rid = getattr(request, "request_id", None)
        request._request_id_token = _request_id_ctx.set(rid)

    def process_response(self, request, response):
        token = getattr(request, "_request_id_token", None)
        if token is not None:
            _request_id_ctx.reset(token)
        return response

    def process_exception(self, request, exception):
        token = getattr(request, "_request_id_token", None)
        if token is not None:
            _request_id_ctx.reset(token)
        return None


class RequestIDLogFilter(logging.Filter):
    """Inject request_id into log records.

    Order of precedence:
    1. record.request_id passed via ``logger.x("...", extra={"request_id": ...})``
    2. ContextVar populated by ``RequestIDLoggingMiddleware``
    3. fallback ``"-"``
    """

    def filter(self, record):
        existing = getattr(record, "request_id", None)
        if existing and existing != "-":
            record.request_id = str(existing)
        else:
            from_ctx = _request_id_ctx.get()
            record.request_id = str(from_ctx) if from_ctx else "-"
        return True


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


_metrics_warn_logger = logging.getLogger("palp.metrics")
_LAST_METRICS_WARN_TS = 0.0
_METRICS_WARN_INTERVAL_SECONDS = 60.0


def _bump_counter(cache, key: str) -> None:
    """Atomically increment a daily counter, seeding it to 0 on first hit.

    Several cache backends (notably django-redis on cold keys, and the LocMem
    backend used in unit tests) raise ValueError when ``incr`` is called on a
    missing key. ``cache.add`` is a no-op when the key already exists, which
    lets us achieve correctness without an extra network round-trip after the
    first request of the day.
    """
    cache.add(key, 0, timeout=60 * 60 * 26)
    cache.incr(key)


def _warn_metrics_failure(operation: str, exc: Exception) -> None:
    global _LAST_METRICS_WARN_TS
    now = time.monotonic()
    if now - _LAST_METRICS_WARN_TS < _METRICS_WARN_INTERVAL_SECONDS:
        return
    _LAST_METRICS_WARN_TS = now
    _metrics_warn_logger.warning(
        "RequestMetricsMiddleware cache %s failed: %s",
        operation, exc,
    )


class RequestMetricsMiddleware(MiddlewareMixin):
    """Increment per-status-class counters in Redis for error-rate SLO tracking.

    Keys: ``palp:http:<date>:2xx``, ``palp:http:<date>:5xx``, ``palp:http:<date>:total``

    Failures are intentionally swallowed so request handling never fails purely
    because the metrics cache is unreachable, but they are surfaced via
    Prometheus + a rate-limited log so we cannot lose visibility silently.
    """

    def process_response(self, request, response):
        from django.core.cache import cache
        from django.utils import timezone

        today = timezone.now().strftime("%Y-%m-%d")
        status_class = f"{response.status_code // 100}xx"
        for key, op in (
            (f"palp:http:{today}:{status_class}", "status_class"),
            (f"palp:http:{today}:total", "total"),
        ):
            try:
                _bump_counter(cache, key)
            except Exception as exc:
                try:
                    from events.metrics import METRICS_MIDDLEWARE_ERRORS

                    METRICS_MIDDLEWARE_ERRORS.labels(operation=op).inc()
                except Exception:
                    pass
                _warn_metrics_failure(op, exc)
        return response
