import os
import json
import urllib.request
import urllib.error

import pytest


BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost")
API_KEY = os.getenv("API_KEY", "sporelink-dev-key")


def request(
    method,
    path,
    data=None,
    api_key=API_KEY,
):
    url = f"{BASE_URL}{path}"

    headers = {}

    if api_key is not None:
        headers["x-api-key"] = api_key

    if data is not None:
        headers["Content-Type"] = "application/json"

    body = None

    if data is not None:
        body = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            response_body = response.read().decode("utf-8")

            try:
                response_data = json.loads(response_body)
            except json.JSONDecodeError:
                response_data = response_body

            return response.status, response_data

    except urllib.error.HTTPError as error:
        response_body = error.read().decode("utf-8")

        try:
            response_data = json.loads(response_body)
        except json.JSONDecodeError:
            response_data = response_body

        return error.code, response_data


# ============================================================
# Test 1 - Health
# ============================================================

def test_health():

    status, data = request(
        "GET",
        "/health",
        api_key=None,
    )

    assert status == 200
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


# ============================================================
# Test 2 - Root
# ============================================================

def test_root():

    status, data = request(
        "GET",
        "/",
        api_key=None,
    )

    assert status == 200
    assert data["service"] == "SporeLink"
    assert data["status"] == "running"


# ============================================================
# Test 3 - Invalid API Key
# ============================================================

def test_invalid_api_key():

    status, data = request(
        "GET",
        "/devices/ROOM-001/latest",
        api_key="wrong-key",
    )

    assert status == 401
    assert data["detail"] == "Missing or invalid API key"


# ============================================================
# Test 4 - Missing API Key
# ============================================================

def test_missing_api_key():

    status, data = request(
        "GET",
        "/devices/ROOM-001/latest",
        api_key=None,
    )

    assert status == 401
    assert data["detail"] == "Missing or invalid API key"


# ============================================================
# Test 5 - Invalid Telemetry
# ============================================================

def test_invalid_telemetry():

    payload = {
        "device_id": "ROOM-TEST",
        "temperature": 500,
        "humidity": 70,
        "co2": 800,
        "substrate_moisture": 60,
    }

    status, data = request(
        "POST",
        "/telemetry",
        data=payload,
    )

    assert status == 422


# ============================================================
# Test 6 - Valid Telemetry
# ============================================================

def test_valid_telemetry():

    payload = {
        "device_id": "ROOM-TEST",
        "temperature": 24.5,
        "humidity": 72,
        "co2": 850,
        "substrate_moisture": 65,
    }

    status, data = request(
        "POST",
        "/telemetry",
        data=payload,
    )

    assert status == 201
    assert data["status"] == "ok"
    assert data["device_id"] == "ROOM-TEST"


# ============================================================
# Test 7 - Latest Reading
# ============================================================

def test_latest():

    status, data = request(
        "GET",
        "/devices/ROOM-TEST/latest",
    )

    assert status == 200
    assert data["device_id"] == "ROOM-TEST"


# ============================================================
# Test 8 - History
# ============================================================

def test_history():

    status, data = request(
        "GET",
        "/devices/ROOM-TEST/history",
    )

    assert status == 200
    assert data["device_id"] == "ROOM-TEST"
    assert data["count"] >= 1


# ============================================================
# Test 9 - Normal Analysis
# ============================================================

def test_normal_analysis():

    payload = {
        "device_id": "ROOM-NORMAL",
        "temperature": 24.0,
        "humidity": 70.0,
        "co2": 800.0,
        "substrate_moisture": 65.0,
    }

    status, data = request(
        "POST",
        "/telemetry",
        data=payload,
    )

    assert status == 201

    status, data = request(
        "GET",
        "/devices/ROOM-NORMAL/analysis",
    )

    assert status == 200
    assert data["analysis"]["status"] == "NORMAL"


# ============================================================
# Test 10 - Anomaly Analysis
# ============================================================

def test_anomaly_analysis():

    payload = {
        "device_id": "ROOM-ANOMALY",
        "temperature": 45.0,
        "humidity": 98.0,
        "co2": 5000.0,
        "substrate_moisture": 10.0,
    }

    status, data = request(
        "POST",
        "/telemetry",
        data=payload,
    )

    assert status == 201

    status, data = request(
        "GET",
        "/devices/ROOM-ANOMALY/analysis",
    )

    assert status == 200
    assert data["analysis"]["status"] == "ANOMALY"
    assert data["analysis"]["risk_score"] > 0


# ============================================================
# Test 11 - Alert
# ============================================================

def test_alert():

    status, data = request(
        "GET",
        "/devices/ROOM-ANOMALY/alerts",
    )

    assert status == 200
    assert data["alert"] is True
    assert data["severity"] == "ANOMALY"
    assert data["risk_score"] > 0


# ============================================================
# Test 12 - Missing Device
# ============================================================

def test_missing_device():

    status, data = request(
        "GET",
        "/devices/DOES-NOT-EXIST/latest",
    )

    assert status == 404