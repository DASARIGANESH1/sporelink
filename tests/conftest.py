"""Pytest configuration — sets required environment variables before app import."""

import os

# These MUST be set before any app code is imported,
# because app/main.py validates them at module load time.
os.environ["API_KEY"] = "sporelink-dev-key"
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://testuser:testpass@localhost:5432/testdb",
)
