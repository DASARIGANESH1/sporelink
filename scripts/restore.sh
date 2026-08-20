#!/usr/bin/env bash
# =============================================================
# SporeLink — Database Restore Script
# =============================================================
# Restores a pg_dump backup into the SporeLink PostgreSQL database.
# Run this from the project root (where docker-compose.yml lives).
#
# Usage: ./scripts/restore.sh <backup_file.sql>
#
# WARNING: This will overwrite existing data in the database.
# The restore uses psql which executes the SQL statements from the backup.
# =============================================================

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <backup_file.sql>"
    echo ""
    echo "Available backups:"
    ls -lh ./backups/*.sql 2>/dev/null || echo "  (no backups found in ./backups/)"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file not found: ${BACKUP_FILE}" >&2
    exit 1
fi

echo "============================================"
echo "SporeLink Database Restore"
echo "============================================"
echo ""
echo "WARNING: This will OVERWRITE existing data."
echo ""
read -p "Type 'yes' to confirm restore from ${BACKUP_FILE}: " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo "[$(date -Iseconds)] Starting database restore from: ${BACKUP_FILE}"

# Restore into the running PostgreSQL container
docker compose exec -T postgres psql -U "${POSTGRES_USER:-sporelink}" "${POSTGRES_DB:-sporelink}" < "$BACKUP_FILE"

echo "[$(date -Iseconds)] Restore completed successfully."
echo ""
echo "Verify the restore:"
echo "  curl http://localhost/devices/<device_id>/latest -H 'x-api-key: YOUR_KEY'"
