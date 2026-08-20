"""Database connection helper for SporeLink."""

import os
import psycopg

DATABASE_URL = os.environ.get("DATABASE_URL", "")


def get_connection():
    """Create and return a new PostgreSQL connection."""
    return psycopg.connect(DATABASE_URL)
