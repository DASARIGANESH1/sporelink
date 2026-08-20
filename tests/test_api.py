"""Unit tests for SporeLink API endpoints.

PostgreSQL is mocked so tests run without a real database.
A separate smoke_test.sh tests against a running Docker container.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from psycopg import OperationalError

from app.main import app

client = TestClient(app)

VALID_HEADERS = {"x-api-key": "sporelink-dev-key"}
VALID_PAYLOAD = {
    "device_id": "dev-001",
    "temperature": 25.0,
    "humidity": 70.0,
    "co2": 400.0,
    "substrate_moisture": 65.0,
}


def _mock_connection(cursor_mock=None):
    """Build a mock psycopg connection with a working cursor context manager."""
    conn = MagicMock()
    if cursor_mock is None:
        cursor_mock = MagicMock()
    # psycopg's cursor.__enter__ returns self, so we must replicate that
    cursor_mock.__enter__ = MagicMock(return_value=cursor_mock)
    cursor_mock.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cursor_mock
    return conn, cursor_mock


# ------------------------------------------------------------------
# Health endpoint
# ------------------------------------------------------------------


@patch("app.main.psycopg.connect")
def test_health_healthy(mock_connect):
    """GET /health returns 200 when PostgreSQL is reachable."""
    mock_connect.return_value = MagicMock()
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["database"] == "connected"
    mock_connect.assert_called_once()


@patch("app.main.psycopg.connect")
def test_health_unhealthy(mock_connect):
    """GET /health returns 503 when PostgreSQL is unreachable."""
    mock_connect.side_effect = OperationalError("connection refused")
    response = client.get("/health")
    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"].lower()


# ------------------------------------------------------------------
# Authentication
# ------------------------------------------------------------------


def test_missing_api_key_returns_401():
    """Requests without x-api-key header are rejected with 401."""
    response = client.post("/telemetry", json=VALID_PAYLOAD)
    assert response.status_code == 401


def test_wrong_api_key_returns_401():
    """Requests with wrong x-api-key are rejected with 401."""
    response = client.post(
        "/telemetry",
        headers={"x-api-key": "wrong-key"},
        json=VALID_PAYLOAD,
    )
    assert response.status_code == 401


# ------------------------------------------------------------------
# Payload validation
# ------------------------------------------------------------------


def test_missing_fields_returns_422():
    """Incomplete payload is rejected with 422."""
    response = client.post(
        "/telemetry",
        headers=VALID_HEADERS,
        json={"device_id": "dev-001"},
    )
    assert response.status_code == 422


def test_out_of_range_temperature_returns_422():
    """Temperature outside valid range is rejected with 422."""
    bad_payload = {**VALID_PAYLOAD, "temperature": 999.0}
    response = client.post(
        "/telemetry",
        headers=VALID_HEADERS,
        json=bad_payload,
    )
    assert response.status_code == 422


def test_negative_humidity_returns_422():
    """Negative humidity is rejected with 422."""
    bad_payload = {**VALID_PAYLOAD, "humidity": -5.0}
    response = client.post(
        "/telemetry",
        headers=VALID_HEADERS,
        json=bad_payload,
    )
    assert response.status_code == 422


# ------------------------------------------------------------------
# POST /telemetry
# ------------------------------------------------------------------

@patch("app.main.get_connection")
def test_post_telemetry_success(mock_get_conn):
    """Valid telemetry is accepted and stored (201)."""
    conn, cursor = _mock_connection()

    cursor.fetchone.return_value = (
        1,
        "dev-001",
        25.0,
        70.0,
        400.0,
        65.0,
        datetime.now(timezone.utc),
    )

    mock_get_conn.return_value = conn

    response = client.post(
        "/telemetry",
        headers=VALID_HEADERS,
        json=VALID_PAYLOAD,
    )

    assert response.status_code == 201

    body = response.json()

    assert body["status"] == "ok"
    assert body["device_id"] == "dev-001"

    cursor.execute.assert_called_once()
    conn.commit.assert_called_once()
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ok"
    assert body["device_id"] == "dev-001"
    cursor.execute.assert_called_once()
    conn.commit.assert_called_once()


# ------------------------------------------------------------------
# GET /devices/{device_id}/latest
# ------------------------------------------------------------------


@patch("app.main.get_connection")
def test_get_latest_success(mock_get_conn):
    """Returns most recent reading for a device (200)."""
    now = datetime.now(timezone.utc)
    cursor = MagicMock()
    cursor.fetchone.return_value = (
    1,
    "dev-001",
    25.0,
    70.0,
    400.0,
    65.0,
    now,
)
    conn, cursor = _mock_connection(cursor)
    mock_get_conn.return_value = conn

    response = client.get("/devices/dev-001/latest", headers=VALID_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["device_id"] == "dev-001"
    assert body["temperature"] == 25.0


@patch("app.main.get_connection")
def test_get_latest_not_found(mock_get_conn):
    """Returns 404 when device has no readings."""
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    conn, cursor = _mock_connection(cursor)
    mock_get_conn.return_value = conn

    response = client.get("/devices/ghost/latest", headers=VALID_HEADERS)
    assert response.status_code == 404


# ------------------------------------------------------------------
# GET /devices/{device_id}/history
# ------------------------------------------------------------------


@patch("app.main.get_connection")
def test_get_history_success(mock_get_conn):
    """Returns paginated history for a device (200)."""
    now = datetime.now(timezone.utc)
    cursor = MagicMock()
    cursor.fetchall.return_value = [
    (1, "dev-001", 25.0, 70.0, 400.0, 65.0, now),
    (2, "dev-001", 24.5, 71.0, 410.0, 64.0, now),
     ]
    conn, cursor = _mock_connection(cursor)
    mock_get_conn.return_value = conn

    response = client.get(
        "/devices/dev-001/history?limit=10&offset=0",
        headers=VALID_HEADERS,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert len(body["readings"]) == 2


@patch("app.main.get_connection")
def test_get_history_not_found(mock_get_conn):
    """Returns 404 when device has no readings."""
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    conn, cursor = _mock_connection(cursor)
    mock_get_conn.return_value = conn

    response = client.get(
        "/devices/ghost/history",
        headers=VALID_HEADERS,
    )
    assert response.status_code == 404


def test_history_limit_bounds():
    """Limit above 100 is rejected by query validation."""
    response = client.get(
        "/devices/dev-001/history?limit=200",
        headers=VALID_HEADERS,
    )
    assert response.status_code == 422
