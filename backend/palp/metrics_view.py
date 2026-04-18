"""IP-restricted Prometheus metrics endpoint.

Defense-in-depth: even though Nginx already restricts the path to internal
networks, the application layer also enforces an allowlist so the endpoint
remains safe if Nginx is misconfigured or bypassed (e.g. direct VPC access).
"""
import ipaddress
import logging

from django.conf import settings
from django.http import HttpResponseForbidden
from django_prometheus.exports import ExportToDjangoView

logger = logging.getLogger("palp.health")

DEFAULT_ALLOWED_NETWORKS = (
    "127.0.0.0/8",
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "::1/128",
    "fc00::/7",
)


def _client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _is_allowed(request) -> bool:
    raw_ip = _client_ip(request)
    if not raw_ip:
        return False
    try:
        client_ip = ipaddress.ip_address(raw_ip)
    except ValueError:
        return False

    allowed_networks = getattr(
        settings, "PALP_METRICS_ALLOWED_NETWORKS", DEFAULT_ALLOWED_NETWORKS,
    )
    for network in allowed_networks:
        try:
            if client_ip in ipaddress.ip_network(network, strict=False):
                return True
        except ValueError:
            logger.warning("Invalid network in PALP_METRICS_ALLOWED_NETWORKS: %s", network)
    return False


def metrics_view(request):
    if not _is_allowed(request):
        logger.warning(
            "Metrics endpoint access denied for %s", _client_ip(request),
        )
        return HttpResponseForbidden("metrics endpoint restricted to internal networks")
    return ExportToDjangoView(request)
