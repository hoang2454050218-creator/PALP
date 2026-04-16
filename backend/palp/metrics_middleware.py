import time

from django.utils.deprecation import MiddlewareMixin

from events.metrics import HTTP_REQUEST_DURATION, HTTP_REQUESTS_TOTAL


def _normalize_endpoint(path: str) -> str:
    """Collapse dynamic path segments into placeholders to limit cardinality."""
    parts = path.strip("/").split("/")
    normalized = []
    for part in parts:
        if part.isdigit():
            normalized.append("{id}")
        else:
            normalized.append(part)
    return "/" + "/".join(normalized) + "/" if normalized else "/"


class PrometheusMetricsMiddleware(MiddlewareMixin):
    """Record HTTP request count and latency as Prometheus metrics."""

    def process_request(self, request):
        request._prom_start = time.monotonic()

    def process_response(self, request, response):
        start = getattr(request, "_prom_start", None)
        if start is None:
            return response

        duration = time.monotonic() - start
        endpoint = _normalize_endpoint(request.path)
        method = request.method

        HTTP_REQUESTS_TOTAL.labels(
            method=method,
            endpoint=endpoint,
            status=response.status_code,
        ).inc()

        HTTP_REQUEST_DURATION.labels(
            method=method,
            endpoint=endpoint,
        ).observe(duration)

        return response
