import os
from app.core.config import settings

# Setup multiprocess environment directory for prometheus_client BEFORE importing prometheus_client
if settings.PROMETHEUS_MULTIPROC_DIR:
    os.environ["PROMETHEUS_MULTIPROC_DIR"] = settings.PROMETHEUS_MULTIPROC_DIR
    os.makedirs(settings.PROMETHEUS_MULTIPROC_DIR, exist_ok=True)

import json
import logging
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from typing import Optional

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    multiprocess,
)
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("prometheus_metrics")


def get_host_ip() -> str:
    """Retrieve host machine / server IP address with fallback mechanisms."""
    if settings.HOST_IP and settings.HOST_IP.strip():
        return settings.HOST_IP.strip()

    env_ip = os.getenv("HOST_IP") or os.getenv("SERVER_IP")
    if env_ip and env_ip.strip():
        return env_ip.strip()

    # Attempt to resolve local outbound IP via socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0.5)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except Exception:
        pass

    # Fallback to resolving hostname
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        if ip:
            return ip
    except Exception:
        pass

    return "127.0.0.1"


def get_hostname() -> str:
    """Retrieve host machine name."""
    if settings.HOST_NAME and settings.HOST_NAME.strip():
        return settings.HOST_NAME.strip()
    env_name = os.getenv("HOST_NAME") or os.getenv("HOSTNAME")
    if env_name and env_name.strip():
        return env_name.strip()
    try:
        return socket.gethostname()
    except Exception:
        return "unknown"


HOST_IP: str = get_host_ip()
HOSTNAME: str = get_hostname()

# Define Core Metrics with Low Overhead & Optimized Buckets
APP_HOST_INFO = Gauge(
    "app_host_info",
    "Application and Host Machine Information",
    ["host_ip", "hostname", "service_name"],
    multiprocess_mode="livesum",
)
APP_HOST_INFO.labels(
    host_ip=HOST_IP,
    hostname=HOSTNAME,
    service_name=settings.PROJECT_NAME,
).set(1)

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total count of HTTP requests processed",
    ["method", "handler", "status", "host_ip"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency duration in seconds",
    ["method", "handler", "host_ip"],
    buckets=(0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)


class PrometheusMiddleware:
    """Pure ASGI Middleware for ultra-fast, zero-overhead Prometheus metric tracking."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.perf_counter()
        method = scope.get("method", "GET")
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            status_code = 500
            raise
        finally:
            duration = time.perf_counter() - start_time
            # Resolve handler / route template for metrics
            state = scope.get("state", {})
            if isinstance(state, dict) and "custom_metric_path" in state:
                handler = state["custom_metric_path"]
            else:
                route = scope.get("route") or scope.get("endpoint")
                if route and hasattr(route, "path"):
                    route_path = route.path
                    # For dynamic routes with {system}, {router}, {path:path} or catch-all {path}, use actual request path
                    if "{path" in route_path or "{system}" in route_path or "{router}" in route_path:
                        handler = scope.get("path", route_path)
                    else:
                        handler = route_path
                else:
                    handler = scope.get("path", "unknown")

            # Update metrics
            try:
                HTTP_REQUESTS_TOTAL.labels(
                    method=method,
                    handler=handler,
                    status=str(status_code),
                    host_ip=HOST_IP,
                ).inc()
                HTTP_REQUEST_DURATION_SECONDS.labels(
                    method=method,
                    handler=handler,
                    host_ip=HOST_IP,
                ).observe(duration)
            except Exception as e:
                logger.debug(f"Error recording metrics: {e}")


def get_latest_metrics() -> bytes:
    """Collect latest metrics from all worker processes via multiprocess collector."""
    registry = CollectorRegistry()
    multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if multiproc_dir and os.path.isdir(multiproc_dir):
        multiprocess.MultiProcessCollector(registry)
    else:
        from prometheus_client import REGISTRY
        registry = REGISTRY
    return generate_latest(registry)


class MetricsHTTPRequestHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler for Prometheus metrics endpoint on dedicated port."""

    def do_GET(self) -> None:
        if self.path == "/metrics":
            try:
                data = get_latest_metrics()
                self.send_response(200)
                self.send_header("Content-Type", CONTENT_TYPE_LATEST)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))
        elif self.path in ("/", "/health"):
            response_body = json.dumps({
                "status": "healthy",
                "service": "prometheus_metrics_server",
                "host_ip": HOST_IP,
                "hostname": HOSTNAME,
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_body)))
            self.end_headers()
            self.wfile.write(response_body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args) -> None:
        # Suppress request logging to stdout/stderr for speed
        pass


class PrometheusMetricsServer:
    """Dedicated background HTTP server for exposing Prometheus metrics on a separate port."""

    def __init__(self, host: str = "0.0.0.0", port: int = 10001):
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self) -> bool:
        if not settings.PROMETHEUS_METRICS_ENABLED:
            return False

        if self.server is not None:
            return True

        try:
            self.server = ThreadingHTTPServer((self.host, self.port), MetricsHTTPRequestHandler)
            self.thread = threading.Thread(
                target=self.server.serve_forever,
                name="PrometheusMetricsServerThread",
                daemon=True,
            )
            self.thread.start()
            logger.info(f"Prometheus Metrics Server successfully listening on http://{self.host}:{self.port}/metrics (Host IP: {HOST_IP})")
            return True
        except OSError:
            # When multiple Uvicorn workers start, only the first binds port 10001.
            # Other workers will safely skip binding while still writing metrics to the multiproc dir.
            logger.info(
                f"Metrics port {self.port} already bound by another worker process. "
                "Metrics collection across workers remains fully operational."
            )
            return False

    def stop(self) -> None:
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
            except Exception as e:
                logger.debug(f"Error stopping metrics server: {e}")
            finally:
                self.server = None


# Global singleton metrics server instance
metrics_server = PrometheusMetricsServer(
    host="0.0.0.0",
    port=settings.PROMETHEUS_METRICS_PORT,
)
