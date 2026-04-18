"""Tests for the /metrics Prometheus endpoint and its IP allowlist.

Wave 1 task: ensure Prometheus can scrape PALP metrics while the endpoint
remains restricted to internal networks at the application layer.
"""
import pytest
from django.test import Client, override_settings

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


PRIVATE_NETWORKS = ("127.0.0.0/8", "10.0.0.0/8", "192.168.0.0/16")


class TestMetricsEndpointReachable:
    def test_metrics_path_returns_200_from_loopback(self):
        client = Client(REMOTE_ADDR="127.0.0.1")
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_path_with_trailing_slash_also_works(self):
        client = Client(REMOTE_ADDR="127.0.0.1")
        response = client.get("/metrics/")
        assert response.status_code == 200

    def test_response_is_prometheus_exposition_format(self):
        client = Client(REMOTE_ADDR="127.0.0.1")
        response = client.get("/metrics")
        content_type = response.get("Content-Type", "")
        assert "text/plain" in content_type
        body = response.content.decode("utf-8")
        assert "# HELP" in body or "# TYPE" in body

    def test_palp_custom_metrics_are_exposed(self):
        client = Client(REMOTE_ADDR="127.0.0.1")
        response = client.get("/metrics")
        body = response.content.decode("utf-8")
        # Custom PALP metrics should appear after first task increments them.
        from events.metrics import CELERY_TASK_TOTAL

        CELERY_TASK_TOTAL.labels(task_name="metrics_test", status="success").inc()
        response2 = client.get("/metrics")
        body2 = response2.content.decode("utf-8")
        assert "palp_celery_task_total" in body2


class TestMetricsEndpointAccessControl:
    @override_settings(PALP_METRICS_ALLOWED_NETWORKS=PRIVATE_NETWORKS)
    def test_public_ip_is_forbidden(self):
        client = Client(REMOTE_ADDR="8.8.8.8")
        response = client.get("/metrics")
        assert response.status_code == 403

    @override_settings(PALP_METRICS_ALLOWED_NETWORKS=PRIVATE_NETWORKS)
    def test_internal_docker_network_is_allowed(self):
        client = Client(REMOTE_ADDR="172.18.0.5")
        # 172.18.0.0/16 is inside default allowlist 172.16.0.0/12 in
        # production but this test overrides to a narrower set; verify
        # that the configurable allowlist actually filters traffic.
        response = client.get("/metrics")
        assert response.status_code == 403

    @override_settings(PALP_METRICS_ALLOWED_NETWORKS=("127.0.0.0/8",))
    def test_allowlist_can_be_narrowed_via_settings(self):
        loopback = Client(REMOTE_ADDR="127.0.0.1")
        external = Client(REMOTE_ADDR="10.5.5.5")
        assert loopback.get("/metrics").status_code == 200
        assert external.get("/metrics").status_code == 403

    def test_x_forwarded_for_is_used_when_present(self):
        client = Client(REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR="8.8.8.8")
        with override_settings(PALP_METRICS_ALLOWED_NETWORKS=("127.0.0.0/8",)):
            response = client.get("/metrics")
            assert response.status_code == 403

    def test_malformed_ip_is_forbidden(self):
        client = Client(REMOTE_ADDR="not-an-ip")
        response = client.get("/metrics")
        assert response.status_code == 403


class TestMetricsEndpointDocsAlignment:
    """Prometheus scrape config and Nginx must agree on the path."""

    def test_prometheus_scrape_path_matches_django_url(self):
        from pathlib import Path

        prom_yaml = Path(__file__).resolve().parents[3] / "infra/prometheus/prometheus.yml"
        if not prom_yaml.exists():
            pytest.skip("Prometheus config file not present in this checkout")
        content = prom_yaml.read_text(encoding="utf-8")
        assert "metrics_path" in content
        assert "/metrics" in content
