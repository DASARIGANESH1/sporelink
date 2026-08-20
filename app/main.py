"""SporeLink - IoT Telemetry Ingestion Service for Nova IoT Systems."""

import os
import sys
import logging

import psycopg
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse
from psycopg import OperationalError

from app.database import get_connection, DATABASE_URL
from app.anomaly import detect_anomaly


# ============================================================
# Configuration
# ============================================================

API_KEY = os.environ.get("API_KEY", "")

_missing = []

if not API_KEY:
    _missing.append("API_KEY")

if not DATABASE_URL:
    _missing.append("DATABASE_URL")

if _missing:
    print(
        f"FATAL: Required environment variable(s) not set: "
        f"{', '.join(_missing)}",
        file=sys.stderr,
    )
    sys.exit(1)


# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        '{"time":"%(asctime)s",'
        '"level":"%(levelname)s",'
        '"message":"%(message)s"}'
    ),
)

logger = logging.getLogger("sporelink")


# ============================================================
# FastAPI Application
# ============================================================

app = FastAPI(
    title="SporeLink",
    version="1.0.0",
    description="IoT telemetry ingestion and monitoring API for SporeLink.",
)


# ============================================================
# Public Endpoints
# ============================================================

PUBLIC_PATHS = {
    "/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
}


# ============================================================
# Swagger / OpenAPI API-Key Security
# ============================================================

def custom_openapi():
    """
    Configure Swagger/OpenAPI to display an API-key
    authentication scheme and Authorize button.
    """

    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="SporeLink",
        version="1.0.0",
        description="IoT telemetry ingestion and monitoring API for SporeLink.",
        routes=app.routes,
    )

    # Define API key authentication
    openapi_schema.setdefault("components", {})

    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "x-api-key",
            "description": "Enter the SporeLink API key.",
        }
    }

    # Protect all non-public endpoints
    for path, path_item in openapi_schema.get("paths", {}).items():

        if path in PUBLIC_PATHS:
            continue

        for operation in path_item.values():

            if isinstance(operation, dict):
                operation["security"] = [
                    {
                        "ApiKeyAuth": []
                    }
                ]

    app.openapi_schema = openapi_schema

    return app.openapi_schema


app.openapi = custom_openapi


# ============================================================
# API-Key Middleware
# ============================================================

@app.middleware("http")
async def api_key_middleware(
    request: Request,
    call_next,
):
    """
    Protect all non-public endpoints using x-api-key.
    """

    # Public endpoints
    if request.url.path in PUBLIC_PATHS:
        return await call_next(request)

    # Read API key
    key = request.headers.get("x-api-key")

    # Validate API key
    if not key or key != API_KEY:

      logger.warning(
        "SECURITY_EVENT: Invalid API key attempt "
        "method=%s path=%s client=%s",
        request.method,
        request.url.path,
        request.client.host if request.client else "unknown",
    )

    return JSONResponse(
        status_code=401,
        content={
            "detail": "Missing or invalid API key"
        },
    )

    return await call_next(request)


# ============================================================
# Pydantic Models
# ============================================================

class TelemetryReading(BaseModel):

    device_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    temperature: float = Field(
        ...,
        ge=-50.0,
        le=100.0,
    )

    humidity: float = Field(
        ...,
        ge=0.0,
        le=100.0,
    )

    co2: float = Field(
        ...,
        ge=0.0,
        le=10000.0,
    )

    substrate_moisture: float = Field(
        ...,
        ge=0.0,
        le=100.0,
    )


# ============================================================
# Root Endpoint
# ============================================================

@app.get("/")
def root():
    return {
        "service": "SporeLink",
        "status": "running",
        "version": "1.0.0",
    }


# ============================================================
# Health Endpoint
# ============================================================

@app.get("/health")
def health_check():
    """
    Health check verifies PostgreSQL connectivity.

    200 -> API and database are healthy
    503 -> Database unavailable
    """

    try:

        conn = psycopg.connect(
            DATABASE_URL,
            connect_timeout=3,
        )

        conn.close()

        return {
            "status": "healthy",
            "database": "connected",
        }

    except OperationalError:

        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )


# ============================================================
# POST /telemetry
# ============================================================

@app.post(
    "/telemetry",
    status_code=201,
)
def create_telemetry(
    reading: TelemetryReading,
):
    """
    Accept and store an IoT telemetry reading.
    """

    conn = get_connection()

    try:

        with conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO telemetry
                (
                    device_id,
                    temperature,
                    humidity,
                    co2,
                    substrate_moisture
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                RETURNING
                    id,
                    device_id,
                    temperature,
                    humidity,
                    co2,
                    substrate_moisture,
                    created_at
                """,
                (
                    reading.device_id,
                    reading.temperature,
                    reading.humidity,
                    reading.co2,
                    reading.substrate_moisture,
                ),
            )

            result = cur.fetchone()

            conn.commit()

        logger.info(
            "Telemetry stored for device=%s",
            reading.device_id,
        )

        return {
            "status": "ok",
            "id": result[0],
            "device_id": result[1],
            "temperature": result[2],
            "humidity": result[3],
            "co2": result[4],
            "substrate_moisture": result[5],
            "created_at": result[6],
        }

    except Exception as exc:

        conn.rollback()

        logger.error(
            "Failed to store telemetry: %s",
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )

    finally:

        conn.close()


# ============================================================
# GET /devices/{device_id}/latest
# ============================================================

@app.get("/devices/{device_id}/latest")
def get_latest(
    device_id: str,
):
    """
    Return the most recent telemetry reading for a device.
    """

    conn = get_connection()

    try:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    id,
                    device_id,
                    temperature,
                    humidity,
                    co2,
                    substrate_moisture,
                    created_at
                FROM telemetry
                WHERE device_id = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (device_id,),
            )

            row = cur.fetchone()

        if row is None:

            raise HTTPException(
                status_code=404,
                detail=(
                    f"No readings found for "
                    f"device '{device_id}'"
                ),
            )

        return {
            "id": row[0],
            "device_id": row[1],
            "temperature": row[2],
            "humidity": row[3],
            "co2": row[4],
            "substrate_moisture": row[5],
            "created_at": row[6],
        }

    finally:

        conn.close()


# ============================================================
# GET /devices/{device_id}/history
# ============================================================

@app.get("/devices/{device_id}/history")
def get_history(
    device_id: str,
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
):
    """
    Return paginated telemetry history.
    """

    conn = get_connection()

    try:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    id,
                    device_id,
                    temperature,
                    humidity,
                    co2,
                    substrate_moisture,
                    created_at
                FROM telemetry
                WHERE device_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                OFFSET %s
                """,
                (
                    device_id,
                    limit,
                    offset,
                ),
            )

            rows = cur.fetchall()

        if not rows:

            raise HTTPException(
                status_code=404,
                detail=(
                    f"No readings found for "
                    f"device '{device_id}'"
                ),
            )

        return {
            "device_id": device_id,
            "limit": limit,
            "offset": offset,
            "count": len(rows),
            "readings": [
                {
                    "id": row[0],
                    "device_id": row[1],
                    "temperature": row[2],
                    "humidity": row[3],
                    "co2": row[4],
                    "substrate_moisture": row[5],
                    "created_at": row[6],
                }
                for row in rows
            ],
        }

    finally:

        conn.close()


# ============================================================
# GET /devices/{device_id}/analysis
# ============================================================

@app.get("/devices/{device_id}/analysis")
def analyze_device(
    device_id: str,
):
    """
    Analyze the latest telemetry reading for anomalies.

    The endpoint retrieves the latest reading from PostgreSQL
    and passes the sensor values to the anomaly detection
    component.
    """

    conn = get_connection()

    try:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    device_id,
                    temperature,
                    humidity,
                    co2,
                    substrate_moisture,
                    created_at
                FROM telemetry
                WHERE device_id = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (device_id,),
            )

            row = cur.fetchone()

        if row is None:

            raise HTTPException(
                status_code=404,
                detail=(
                    f"No readings found for "
                    f"device '{device_id}'"
                ),
            )

        # Run anomaly detection
        result = detect_anomaly(
            temperature=row[1],
            humidity=row[2],
            co2=row[3],
            substrate_moisture=row[4],
        )

        return {
            "device_id": row[0],

            "telemetry": {
                "temperature": row[1],
                "humidity": row[2],
                "co2": row[3],
                "substrate_moisture": row[4],
                "created_at": row[5],
            },

            "analysis": {
                "status": result.status,
                "risk_score": result.risk_score,
                "reasons": result.reasons,
            },
        }

    finally:

        conn.close()


# ============================================================
# GET /devices/{device_id}/alerts
# ============================================================

@app.get("/devices/{device_id}/alerts")
def get_alert(
    device_id: str,
):
    """
    Return an alert based on the latest telemetry analysis.
    """

    conn = get_connection()

    try:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    device_id,
                    temperature,
                    humidity,
                    co2,
                    substrate_moisture,
                    created_at
                FROM telemetry
                WHERE device_id = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (device_id,),
            )

            row = cur.fetchone()

        if row is None:

            raise HTTPException(
                status_code=404,
                detail=(
                    f"No readings found for "
                    f"device '{device_id}'"
                ),
            )

        # Analyze latest reading
        result = detect_anomaly(
            temperature=row[1],
            humidity=row[2],
            co2=row[3],
            substrate_moisture=row[4],
        )

        alert = result.status != "NORMAL"

        return {
            "device_id": row[0],
            "alert": alert,
            "severity": result.status,
            "risk_score": result.risk_score,
            "reasons": result.reasons,
            "created_at": row[5],
        }

    finally:

        conn.close()