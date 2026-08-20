-- SporeLink Database Migration: Create telemetry table
-- Version: 001
-- Description: Initial schema for IoT telemetry data

CREATE TABLE IF NOT EXISTS telemetry (
    id              SERIAL PRIMARY KEY,
    device_id       VARCHAR(100) NOT NULL,
    temperature     DOUBLE PRECISION NOT NULL,
    humidity        DOUBLE PRECISION NOT NULL,
    co2             DOUBLE PRECISION NOT NULL,
    substrate_moisture DOUBLE PRECISION NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_telemetry_device_id ON telemetry(device_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_created_at ON telemetry(created_at DESC);
