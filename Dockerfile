# ==============================================================================
# Multi-Stage Dockerfile for Municipal Citizen Grievance Platform
# SIMATS Engineering - CSA10 Software Engineering (CO3)
# ==============================================================================

# Stage 1: Build stage (compile dependencies)
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Final runtime stage
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DATABASE_PATH=/app/data/grievances.db

# Install runtime dependencies (curl for container healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder stage
COPY --from=builder /install /usr/local

# Create non-root application user for container security
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -s /bin/bash -m appuser

# Copy application source code
COPY --chown=appuser:appgroup backend/ ./backend/
COPY --chown=appuser:appgroup frontend/ ./frontend/
COPY --chown=appuser:appgroup tests/ ./tests/
COPY --chown=appuser:appgroup pytest.ini .

# Create persistent data directory and set permissions
RUN mkdir -p /app/data && chown -R appuser:appgroup /app/data

USER appuser

EXPOSE 8000

# Container health monitoring
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/healthz || exit 1

CMD ["python", "-m", "backend.app"]
