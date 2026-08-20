# ============================================================
# SporeLink — Multi-stage Production Dockerfile
# ============================================================

# -------------------------
# Stage 1: Build
# -------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .

# Create isolated virtual environment
RUN python -m venv /opt/venv

# Install all Python dependencies into the virtual environment
RUN /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


# -------------------------
# Stage 2: Runtime
# -------------------------
FROM python:3.12-slim

# Install PostgreSQL runtime library and create non-root user
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r sporelink \
    && useradd -r -g sporelink -d /app -s /usr/sbin/nologin sporelink

WORKDIR /app

# Copy the complete virtual environment
COPY --from=builder /opt/venv /opt/venv

# Use the virtual environment by default
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy application
COPY app/ ./app/
COPY migrations/ ./migrations/

# Give application ownership to non-root user
RUN chown -R sporelink:sporelink /app

# Run as non-root
USER sporelink

EXPOSE 8000

# Database-aware application health check
HEALTHCHECK --interval=30s \
            --timeout=5s \
            --start-period=15s \
            --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]