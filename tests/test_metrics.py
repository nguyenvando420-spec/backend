import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.metrics import metrics_server, get_latest_metrics, HOST_IP, HOSTNAME
from app.core.config import settings


@pytest.mark.asyncio
async def test_metrics_server_lifecycle():
    """Test that the metrics server is running, exposes /metrics and /health with host_ip."""
    metrics_server.start()

    async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{settings.PROMETHEUS_METRICS_PORT}") as client:
        # Check health endpoint on metrics server
        health_res = await client.get("/health")
        assert health_res.status_code == 200
        health_data = health_res.json()
        assert health_data["status"] == "healthy"
        assert "host_ip" in health_data and len(health_data["host_ip"]) > 0
        assert "hostname" in health_data and len(health_data["hostname"]) > 0

        # Check metrics endpoint
        metrics_res = await client.get("/metrics")
        assert metrics_res.status_code == 200
        assert metrics_res.headers["content-type"].startswith("text/plain")
        metrics_text = metrics_res.text
        assert "app_host_info" in metrics_text
        assert 'host_ip="' in metrics_text


@pytest.mark.asyncio
async def test_metrics_middleware_tracking():
    """Test that requests through FastAPI increment Prometheus metrics with host_ip label."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Trigger root endpoint
        res = await client.get("/")
        assert res.status_code == 200
        assert res.json()["host_ip"] == HOST_IP

        # Trigger health endpoint
        res_health = await client.get("/health")
        assert res_health.status_code == 200
        assert res_health.json()["host_ip"] == HOST_IP

        # Trigger items endpoint
        res2 = await client.get("/api/v1/items")
        assert res2.status_code == 200

    # Verify metrics generated include host_ip
    raw_metrics = get_latest_metrics().decode("utf-8")
    assert "http_requests_total" in raw_metrics
    assert f'host_ip="{HOST_IP}"' in raw_metrics
