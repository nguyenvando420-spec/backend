import atexit
import glob
import json
import logging
import os
import socket
import threading
import time
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("prometheus_metrics")


def is_pid_alive(pid: int) -> bool:
    """Check if a process ID is currently running."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def is_stale_metric_file(filename: str) -> bool:
    """
    Check if a multiprocess metric file (.db, .tmp) is stale.
    Returns True if the file belongs to a dead process or is a temporary file.
    """
    if filename.endswith(".tmp"):
        return True

    if not filename.endswith(".db"):
        return False

    # Prometheus db files format: <type>_<pid>.db or <type>_<mode>_<pid>.db
    parts = filename[:-3].rsplit("_", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return not is_pid_alive(int(parts[1]))

    return True


def _remove_file_safely(file_path: str) -> None:
    """Safely remove a file, suppressing and logging any filesystem errors."""
    try:
        os.remove(file_path)
    except Exception as e:
        logger.debug(f"Error removing stale metrics file {file_path}: {e}")


def clean_multiproc_dir(path: Optional[str] = None, clean_all: bool = False) -> None:
    """
    Clean up old metrics files (.db, .tmp) from the multiprocess directory.

    :param path: Path to the multiprocess directory.
    :param clean_all: If True, remove all metric files in directory unconditionally.
                      If False, remove only files belonging to dead/terminated PIDs.
    """
    dir_path = path or os.environ.get("PROMETHEUS_MULTIPROC_DIR") or settings.PROMETHEUS_MULTIPROC_DIR
    if not dir_path or not os.path.isdir(dir_path):
        return

    try:
        for filename in os.listdir(dir_path):
            file_path = os.path.join(dir_path, filename)
            if not os.path.isfile(file_path):
                continue

            if clean_all or is_stale_metric_file(filename):
                _remove_file_safely(file_path)
    except Exception as e:
        logger.debug(f"Error scanning multiprocess directory {dir_path}: {e}")


# Setup multiprocess environment directory for prometheus_client BEFORE importing prometheus_client
if settings.PROMETHEUS_MULTIPROC_DIR:
    os.environ["PROMETHEUS_MULTIPROC_DIR"] = settings.PROMETHEUS_MULTIPROC_DIR
    os.makedirs(settings.PROMETHEUS_MULTIPROC_DIR, exist_ok=True)
    # Automatically clean up stale metrics from previous runs / terminated processes
    clean_multiproc_dir(settings.PROMETHEUS_MULTIPROC_DIR, clean_all=False)


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


def cleanup_current_process_metrics() -> None:
    """Cleanup multiprocess metrics files for the current process upon exit or shutdown."""
    try:
        pid = os.getpid()
        multiprocess.mark_process_dead(pid)
        dir_path = os.environ.get("PROMETHEUS_MULTIPROC_DIR") or settings.PROMETHEUS_MULTIPROC_DIR
        if dir_path and os.path.isdir(dir_path):
            for pattern in (f"*_{pid}.db", f"*_{pid}_*.db"):
                for f in glob.glob(os.path.join(dir_path, pattern)):
                    try:
                        os.remove(f)
                    except Exception:
                        pass
    except Exception as e:
        logger.debug(f"Error cleaning up current process metrics: {e}")


atexit.register(cleanup_current_process_metrics)



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

# ==========================================
# 🔹 TẦNG 1: GLOBAL METRICS (BÁO CÁO TỔNG QUAN - 100% TRAFFIC)
# ==========================================
HTTP_GLOBAL_REQUESTS_INCOMING_TOTAL = Counter(
    "http_global_requests_incoming_total",
    "Total count of incoming HTTP requests received by the server",
    ["method", "host_ip"],
)

HTTP_GLOBAL_RESPONSES_TOTAL = Counter(
    "http_global_responses_total",
    "Total count of completed HTTP responses returned by the server",
    ["method", "status", "host_ip"],
)

HTTP_GLOBAL_REQUESTS_IN_FLIGHT = Gauge(
    "http_global_requests_in_flight",
    "Current number of HTTP requests currently being processed",
    ["host_ip"],
    multiprocess_mode="livesum",
)

HTTP_GLOBAL_REQUEST_DURATION_SECONDS = Histogram(
    "http_global_request_duration_seconds",
    "Global HTTP request latency distribution across all routes",
    ["method", "host_ip"],
    buckets=(0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# ==========================================
# 🔸 TẦNG 2: DETAILED METRICS (BÁO CÁO RIÊNG TỪNG ROUTER - CÓ THỂ ẨN / HIDE)
# Chỉ ghi nhận khi Router đó được BẬT (không bị exclude)
# ==========================================
HTTP_REQUESTS_INCOMING_TOTAL = Counter(
    "http_requests_incoming_total",
    "Detailed count of incoming HTTP requests for enabled routers",
    ["method", "handler", "host_ip", "api_group"],
)

HTTP_RESPONSES_TOTAL = Counter(
    "http_responses_total",
    "Detailed count of completed HTTP responses for enabled routers",
    ["method", "handler", "status", "host_ip", "api_group"],
)

HTTP_REQUESTS_IN_FLIGHT = Gauge(
    "http_requests_in_flight",
    "Current number of HTTP requests currently being processed for enabled routers",
    ["api_group", "host_ip"],
    multiprocess_mode="livesum",
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "Detailed HTTP request latency for enabled routers",
    ["method", "handler", "host_ip", "api_group"],
    buckets=(0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)


@lru_cache(maxsize=1024)
def fast_extract_api_group(path: str) -> str:
    """
    Trích xuất api_group từ URL path với tốc độ nano-giây (~40ns).
    Tự động nhận diện 100% router mới (/api/v1/items, /api/v1/users,...)
    và dynamic routers (/api/v1/{system}/{router}/..., /{system}/{router}/...).
    """
    if path in ("/", "/health", "/docs", "/redoc", "/openapi.json"):
        return "System"

    path_clean = path.strip("/")
    if not path_clean:
        return "System"

    segments = path_clean.split("/")

    # Xử lý router có tiền tố /api/v1/..., /api/v2/...
    if segments[0] == "api":
        if len(segments) >= 3:
            # e.g. api/v1/items -> "Items", api/v1/user-profiles -> "User Profiles", api/v1/auth -> "Auth"
            return segments[2].replace("-", " ").replace("_", " ").title()
        elif len(segments) == 2:
            return segments[1].title()
        return "System"

    # Xử lý router không có tiền tố /api (e.g. /users/list -> "Users", /crm/users -> "Crm", /billing/pay -> "Billing")
    if segments:
        return segments[0].replace("-", " ").replace("_", " ").title()

    return "System"


class PrometheusMiddleware:
    """Pure ASGI Middleware for ultra-fast, zero-overhead Prometheus 2-tier metric tracking."""

    def __init__(self, app: ASGIApp):
        self.app = app
        raw_paths = getattr(settings, "PROMETHEUS_EXCLUDED_PATHS", "")
        self.excluded_paths = tuple(p.strip() for p in raw_paths.split(",") if p.strip())

        raw_tags = getattr(settings, "PROMETHEUS_EXCLUDED_TAGS", "")
        self.excluded_tags = {t.strip().lower() for t in raw_tags.split(",") if t.strip()}

    def _resolve_api_group(self, path: str) -> Optional[str]:
        """Fast extraction of api_group, respecting path and tag exclusions."""
        if self.excluded_paths and path.startswith(self.excluded_paths):
            return None

        api_group = fast_extract_api_group(path)
        if api_group and api_group.lower() not in self.excluded_tags:
            return api_group
        return None

    def _record_incoming(self, method: str, api_group: Optional[str]) -> None:
        """Record incoming global requests and increment in-flight gauges."""
        try:
            HTTP_GLOBAL_REQUESTS_INCOMING_TOTAL.labels(method=method, host_ip=HOST_IP).inc()
            HTTP_GLOBAL_REQUESTS_IN_FLIGHT.labels(host_ip=HOST_IP).inc()
            if api_group:
                HTTP_REQUESTS_IN_FLIGHT.labels(api_group=api_group, host_ip=HOST_IP).inc()
        except Exception as e:
            logger.debug(f"Error recording incoming request metrics: {e}")

    def _record_global_response(
        self, method: str, status_code: int, duration: float, api_group: Optional[str]
    ) -> None:
        """Record global completed response, decrement in-flight gauges, and observe latency."""
        try:
            HTTP_GLOBAL_REQUESTS_IN_FLIGHT.labels(host_ip=HOST_IP).dec()
            HTTP_GLOBAL_RESPONSES_TOTAL.labels(
                method=method,
                status=str(status_code),
                host_ip=HOST_IP,
            ).inc()
            HTTP_GLOBAL_REQUEST_DURATION_SECONDS.labels(
                method=method,
                host_ip=HOST_IP,
            ).observe(duration)
            if api_group:
                HTTP_REQUESTS_IN_FLIGHT.labels(api_group=api_group, host_ip=HOST_IP).dec()
        except Exception as e:
            logger.debug(f"Error recording global response metrics: {e}")

    def _is_detailed_tracking_enabled(
        self, scope: Scope, path: str, api_group: Optional[str]
    ) -> bool:
        """Check if detailed (Tier 2) metric tracking is enabled for this route."""
        if not api_group:
            return False

        if self.excluded_paths and path.startswith(self.excluded_paths):
            return False

        state = scope.get("state")
        if isinstance(state, dict) and state.get("skip_metrics") is True:
            return False

        route = scope.get("route") or scope.get("endpoint")
        if route and hasattr(route, "tags") and route.tags:
            if any(t.lower() in self.excluded_tags for t in route.tags):
                return False

        return True

    @staticmethod
    def _resolve_handler_path(scope: Scope, path: str) -> str:
        """Resolve endpoint handler template or custom metric path."""
        state = scope.get("state")
        if isinstance(state, dict) and "custom_metric_path" in state:
            return str(state["custom_metric_path"])

        route = scope.get("route") or scope.get("endpoint")
        if not (route and hasattr(route, "path")):
            return scope.get("path", "unknown")

        route_path: str = route.path
        if any(token in route_path for token in ("{path", "{system}", "{router}")):
            return scope.get("path", route_path)
        return route_path

    def _record_detailed_metrics(
        self,
        scope: Scope,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        api_group: str,
    ) -> None:
        """Record detailed Tier-2 router metrics (incoming, response, latency)."""
        handler = self._resolve_handler_path(scope, path)
        state = scope.get("state")
        final_group = (
            state.get("custom_api_group", api_group)
            if isinstance(state, dict)
            else api_group
        )

        try:
            HTTP_REQUESTS_INCOMING_TOTAL.labels(
                method=method,
                handler=handler,
                host_ip=HOST_IP,
                api_group=final_group,
            ).inc()
            HTTP_RESPONSES_TOTAL.labels(
                method=method,
                handler=handler,
                status=str(status_code),
                host_ip=HOST_IP,
                api_group=final_group,
            ).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method,
                handler=handler,
                host_ip=HOST_IP,
                api_group=final_group,
            ).observe(duration)
        except Exception as e:
            logger.debug(f"Error recording detailed metrics: {e}")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET")
        path = scope.get("path", "")
        api_group = self._resolve_api_group(path)

        self._record_incoming(method, api_group)

        start_time = time.perf_counter()
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
            self._record_global_response(method, status_code, duration, api_group)

            if api_group and self._is_detailed_tracking_enabled(scope, path, api_group):
                self._record_detailed_metrics(
                    scope, method, path, status_code, duration, api_group
                )


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
