#!/usr/bin/env bash
# smoke_test.sh — Basic API smoke test against a running SporeLink instance.
# Usage: ./smoke_test.sh [BASE_URL]
# Defaults to http://localhost

set -euo pipefail

BASE_URL="${1:-http://localhost}"
API_KEY="${API_KEY:-change-me}"
PASS=0
FAIL=0

pass() { echo "  ✓ $1"; PASS=$((PASS + 1)); }
fail() { echo "  ✗ $1"; FAIL=$((FAIL + 1)); }

echo "=== SporeLink Smoke Test ==="
echo "Target: $BASE_URL"
echo ""

# 1. Health check
STATUS=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/health")
if [ "$STATUS" = "200" ]; then pass "GET /health → 200"; else fail "GET /health → expected 200, got $STATUS"; fi

# 2. POST telemetry
STATUS=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE_URL/telemetry" \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"device_id":"smoke-dev-001","temperature":23.5,"humidity":72.0,"co2":410.0,"substrate_moisture":60.0}')
if [ "$STATUS" = "201" ]; then pass "POST /telemetry → 201"; else fail "POST /telemetry → expected 201, got $STATUS"; fi

# 3. Missing API key → 401
STATUS=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE_URL/telemetry" \
  -H "Content-Type: application/json" \
  -d '{"device_id":"smoke-dev-001","temperature":23.5,"humidity":72.0,"co2":410.0,"substrate_moisture":60.0}')
if [ "$STATUS" = "401" ]; then pass "POST /telemetry (no key) → 401"; else fail "POST /telemetry (no key) → expected 401, got $STATUS"; fi

# 4. GET latest
STATUS=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/devices/smoke-dev-001/latest" \
  -H "x-api-key: $API_KEY")
if [ "$STATUS" = "200" ]; then pass "GET /latest → 200"; else fail "GET /latest → expected 200, got $STATUS"; fi

# 5. GET history
STATUS=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/devices/smoke-dev-001/history?limit=5" \
  -H "x-api-key: $API_KEY")
if [ "$STATUS" = "200" ]; then pass "GET /history → 200"; else fail "GET /history → expected 200, got $STATUS"; fi

echo ""
echo "Results: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then exit 1; fi
