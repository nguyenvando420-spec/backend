FROM python:3.11-slim

# Prevent Python from writing .pyc files & buffer output for real-time logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc_dir

# Set working directory
WORKDIR /app

# Install system dependencies (curl for container healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directory for prometheus multiprocess metrics
RUN mkdir -p /tmp/prometheus_multiproc_dir

# Copy application source code
COPY . .

# Expose FastAPI Web API (8000) and Prometheus Metrics Server (10001)
EXPOSE 8000 10001

# Healthcheck for backend container
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run Uvicorn with 4 workers for high concurrency & performance
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
