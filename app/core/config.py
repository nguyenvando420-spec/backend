import os
from typing import Optional

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):
        PROJECT_NAME: str = "FastAPI Clean Architecture Demo"
        API_V1_STR: str = "/api/v1"
        DATABASE_URL: str = "sqlite+aiosqlite:///./sql_app.db"
        USE_MOCK_DB: bool = False

        # Prometheus Metrics Settings
        PROMETHEUS_METRICS_ENABLED: bool = True
        PROMETHEUS_METRICS_PORT: int = 10001
        PROMETHEUS_MULTIPROC_DIR: str = "/tmp/prometheus_multiproc_dir"

        # Host Machine Info for Metrics
        HOST_IP: Optional[str] = None
        HOST_NAME: Optional[str] = None

        model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

except ImportError:
    # Fallback if pydantic_settings is not yet installed
    class Settings:  # type: ignore
        PROJECT_NAME: str = "FastAPI Clean Architecture Demo"
        API_V1_STR: str = "/api/v1"
        DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./sql_app.db")
        USE_MOCK_DB: bool = os.getenv("USE_MOCK_DB", "false").lower() == "true"
        PROMETHEUS_METRICS_ENABLED: bool = os.getenv("PROMETHEUS_METRICS_ENABLED", "true").lower() == "true"
        PROMETHEUS_METRICS_PORT: int = int(os.getenv("PROMETHEUS_METRICS_PORT", "10001"))
        PROMETHEUS_MULTIPROC_DIR: str = os.getenv("PROMETHEUS_MULTIPROC_DIR", "/tmp/prometheus_multiproc_dir")
        HOST_IP: Optional[str] = os.getenv("HOST_IP")
        HOST_NAME: Optional[str] = os.getenv("HOST_NAME")

settings = Settings()
