from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.metrics import (
    PrometheusMiddleware,
    metrics_server,
    cleanup_current_process_metrics,
    HOST_IP,
    HOSTNAME,
)
from app.domain.exceptions.item_exceptions import (
    ItemNotFoundException,
    ItemAlreadyExistsException,
    InvalidItemDataException,
)
from app.infrastructure.database.connection import init_db
from app.api.v1.routers.item_router import router as item_router
from app.api.v1.routers.dynamic_router import router as dynamic_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown actions."""
    # Startup: Initialize DB tables
    await init_db()
    
    # Startup: Start dedicated Prometheus metrics server on port 10001
    metrics_server.start()
    
    yield
    
    # Shutdown: Stop metrics server & cleanup metrics
    metrics_server.stop()
    cleanup_current_process_metrics()



app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add Prometheus ASGI Middleware for ultra-fast metric tracking
app.add_middleware(PrometheusMiddleware)

# Exception Handlers mapping Domain Exceptions to HTTP Status Codes
@app.exception_handler(ItemNotFoundException)
async def item_not_found_handler(request: Request, exc: ItemNotFoundException):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.message, "code": "ITEM_NOT_FOUND"}
    )


@app.exception_handler(ItemAlreadyExistsException)
async def item_already_exists_handler(request: Request, exc: ItemAlreadyExistsException):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": exc.message, "code": "ITEM_ALREADY_EXISTS"}
    )


@app.exception_handler(InvalidItemDataException)
async def invalid_item_data_handler(request: Request, exc: InvalidItemDataException):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message, "code": "INVALID_ITEM_DATA"}
    )


# Register Routers
app.include_router(item_router, prefix=settings.API_V1_STR)
app.include_router(dynamic_router, prefix=settings.API_V1_STR)
app.include_router(dynamic_router)


@app.get("/", tags=["Health"])
async def root():
    return {
        "message": "Welcome to FastAPI Clean Architecture Demo API",
        "host_ip": HOST_IP,
        "hostname": HOSTNAME,
        "docs": "/docs",
        "metrics_port": settings.PROMETHEUS_METRICS_PORT
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "fastapi_backend",
        "host_ip": HOST_IP,
        "hostname": HOSTNAME
    }

