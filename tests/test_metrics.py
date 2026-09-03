import os
import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.metrics import (
    metrics_server,
    get_latest_metrics,
    clean_multiproc_dir,
    fast_extract_api_group,
    HOST_IP,
    HOSTNAME,
)
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
    assert "http_responses_total" in raw_metrics
    assert "http_requests_incoming_total" in raw_metrics
    assert f'host_ip="{HOST_IP}"' in raw_metrics


@pytest.mark.asyncio
async def test_dynamic_api_metrics_tracking():
    """Test that dynamic routes /{system}/{router}/{path:path} display exact resolved paths in metrics instead of generic template."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Call dynamic route directly: /crm/users/profile
        res1 = await client.get("/crm/users/profile")
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["system"] == "crm"
        assert data1["router"] == "users"
        assert data1["path"] == "profile"

        # 2. Call dynamic route with nested path: /billing/invoices/pay/v1
        res2 = await client.post("/billing/invoices/pay/v1", json={"amount": 500})
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["system"] == "billing"
        assert data2["router"] == "invoices"
        assert data2["path"] == "pay/v1"
        assert data2["body"] == {"amount": 500}

        # 3. Call dynamic route under /api/v1 prefix: /api/v1/auth/oauth/callback/google
        res3 = await client.get("/api/v1/auth/oauth/callback/google?code=xyz")
        assert res3.status_code == 200
        data3 = res3.json()
        assert data3["system"] == "auth"
        assert data3["router"] == "oauth"
        assert data3["path"] == "callback/google"
        assert data3["query_params"] == {"code": "xyz"}

    # Verify Prometheus Metrics text contains exact paths, NOT the generic template
    raw_metrics = get_latest_metrics().decode("utf-8")

    # Exact paths should be recorded in metrics labels
    assert 'handler="/crm/users/profile"' in raw_metrics
    assert 'handler="/billing/invoices/pay/v1"' in raw_metrics
    assert 'handler="/api/v1/auth/oauth/callback/google"' in raw_metrics

    # Verify api_group matches across all metrics
    assert 'api_group="Crm"' in raw_metrics
    assert 'api_group="Billing"' in raw_metrics
    assert 'api_group="Auth"' in raw_metrics

    # The generic placeholder template must NOT be present in metrics
    assert 'handler="/{system}/{router}/{path:path}"' not in raw_metrics
    assert 'handler="/api/v1/{system}/{router}/{path:path}"' not in raw_metrics


def test_clean_multiproc_dir_removes_stale_files():
    """Test that clean_multiproc_dir removes files from dead processes and leaves active ones."""
    import tempfile
    from app.core.metrics import clean_multiproc_dir

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a stale file with a non-existent PID (e.g. 999999)
        stale_file = os.path.join(temp_dir, "counter_999999.db")
        with open(stale_file, "w") as f:
            f.write("stale_data")

        # Create a file for the current alive process
        current_pid = os.getpid()
        active_file = os.path.join(temp_dir, f"counter_{current_pid}.db")
        with open(active_file, "w") as f:
            f.write("active_data")

        assert os.path.exists(stale_file)
        assert os.path.exists(active_file)

        # Run cleanup with clean_all=False (normal startup mode)
        clean_multiproc_dir(path=temp_dir, clean_all=False)

        # Stale file should be deleted, active file preserved
        assert not os.path.exists(stale_file)
        assert os.path.exists(active_file)

        # Run cleanup with clean_all=True (force wipe mode)
        clean_multiproc_dir(path=temp_dir, clean_all=True)
        assert not os.path.exists(active_file)


def test_is_stale_metric_file_logic():
    """Test individual file stale detection logic for .tmp, .db, and other files."""
    from app.core.metrics import is_stale_metric_file

    current_pid = os.getpid()

    # 1. Temporary files always stale
    assert is_stale_metric_file("metrics_123.tmp") is True

    # 2. Non-metric files ignored
    assert is_stale_metric_file("readme.txt") is False
    assert is_stale_metric_file(".gitkeep") is False

    # 3. Active PID db file preserved
    assert is_stale_metric_file(f"counter_{current_pid}.db") is False
    assert is_stale_metric_file(f"gauge_livesum_{current_pid}.db") is False

    # 4. Dead / invalid PID db file is stale
    assert is_stale_metric_file("counter_999999.db") is True
    assert is_stale_metric_file("invalid_db_without_pid.db") is True


@pytest.mark.asyncio
async def test_metrics_api_group_and_exclusions():
    """Test that api_group label is separated and excluded routers/paths/flags are not tracked."""
    from fastapi import APIRouter, Request, FastAPI
    from app.core.metrics import PrometheusMiddleware

    test_app = FastAPI()
    test_app.add_middleware(PrometheusMiddleware)

    # 1. Router with normal tag
    user_router = APIRouter(prefix="/users", tags=["Users"])
    @user_router.get("/list")
    async def list_users():
        return {"users": []}

    # 2. Router with excluded tag
    secret_router = APIRouter(prefix="/secret", tags=["no-metrics"])
    @secret_router.get("/data")
    async def secret_data():
        return {"secret": True}

    # 3. Endpoint that programmatically skips metrics
    @test_app.get("/skip-endpoint")
    async def skip_endpoint(request: Request):
        request.state.skip_metrics = True
        return {"skipped": True}

    test_app.include_router(user_router)
    test_app.include_router(secret_router)

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Call normal user endpoint
        res1 = await client.get("/users/list")
        assert res1.status_code == 200

        # Call secret router endpoint (should be skipped)
        res2 = await client.get("/secret/data")
        assert res2.status_code == 200

        # Call skip-endpoint (should be skipped)
        res3 = await client.get("/skip-endpoint")
        assert res3.status_code == 200

        # Call excluded path (/docs)
        res4 = await client.get("/docs")
        # May be 404 on subapp without docs registered, but middleware should intercept path

    raw_metrics = get_latest_metrics().decode("utf-8")

    # 1. Tầng 1 (Global Metrics): Luôn ghi nhận toàn bộ requests và responses (100% traffic)
    assert "http_global_requests_incoming_total" in raw_metrics
    assert "http_global_responses_total" in raw_metrics
    assert "http_global_requests_in_flight" in raw_metrics
    assert "http_global_request_duration_seconds" in raw_metrics

    # 2. Tầng 2 (Detailed Metrics): Chỉ ghi nhận các Router được bật
    # Router "Users" được bật -> Có đầy đủ incoming, response, duration với api_group="Users"
    assert "http_requests_incoming_total" in raw_metrics
    assert "http_responses_total" in raw_metrics
    assert "http_request_duration_seconds" in raw_metrics
    assert 'api_group="Users"' in raw_metrics
    assert 'handler="/users/list"' in raw_metrics

    # Router "no-metrics", "skip-endpoint", "/docs" bị tắt ở tầng chi tiết -> KHÔNG xuất hiện trong Tầng 2
    assert 'handler="/secret/data"' not in raw_metrics
    assert 'handler="/skip-endpoint"' not in raw_metrics
    assert 'handler="/docs"' not in raw_metrics


def test_fast_extract_api_group():
    """Test fast nano-second extraction of api_group for static, dynamic, and system routes."""
    # 1. System routes
    assert fast_extract_api_group("/") == "System"
    assert fast_extract_api_group("/health") == "System"
    assert fast_extract_api_group("/docs") == "System"
    assert fast_extract_api_group("/redoc") == "System"
    assert fast_extract_api_group("/openapi.json") == "System"

    # 2. Standard API routes under /api/v1 (static & dynamic)
    assert fast_extract_api_group("/api/v1/items") == "Items"
    assert fast_extract_api_group("/api/v1/items/123") == "Items"
    assert fast_extract_api_group("/api/v1/users") == "Users"
    assert fast_extract_api_group("/api/v1/user-profiles/info") == "User Profiles"
    assert fast_extract_api_group("/api/v1/order_items/345") == "Order Items"
    assert fast_extract_api_group("/api/v1/auth/oauth/callback/google") == "Auth"

    # 3. Dynamic routes without /api/v1 prefix
    assert fast_extract_api_group("/crm/users/profile") == "Crm"
    assert fast_extract_api_group("/billing/invoices/pay/v1") == "Billing"
    assert fast_extract_api_group("/users/list") == "Users"


@pytest.mark.asyncio
async def test_metrics_middleware_does_not_swallow_exceptions():
    """Test that unhandled exceptions from downstream are not swallowed by finally block."""
    from fastapi import FastAPI
    from app.core.metrics import PrometheusMiddleware

    test_app = FastAPI()
    test_app.add_middleware(PrometheusMiddleware)

    @test_app.get("/error-endpoint")
    async def error_endpoint():
        raise RuntimeError("Custom server crash")

    transport = ASGITransport(app=test_app, raise_app_exceptions=True)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with pytest.raises(RuntimeError, match="Custom server crash"):
            await client.get("/error-endpoint")




