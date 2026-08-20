#!/usr/bin/env bash
# =============================================================
# SporeLink — Database Backup Script
# =============================================================
# Creates a pg_dump of the SporeLink PostgreSQL database.
# Run this from the project root (where docker-compose.yml lives).
#
# Usage: ./scripts/backup.sh [output_directory]
#   Default output: ./backups/
#
# Recommended: Run via cron for automated backups.
#   Example (daily at 2 AM):
#     0 2 * * * cd /path/to/SporeLink && ./scripts/backup.sh /mnt/backups/sporelink
# =============================================================

set -euo pipefail

BACKUP_DIR="${1:-./backups}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/sporelink_backup_${TIMESTAMP}.sql"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "[$(date -Iseconds)] Starting SporeLink database backup..."
echo "  Backup file: ${BACKUP_FILE}"

# Run pg_dump against the running PostgreSQL container
docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-sporelink}" "${POSTGRES_DB:-sporelink}" > "$BACKUP_FILE"

# Verify the backup was created and is non-empty
if [ ! -s "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file is empty or was not created." >&2
    exit 1
fi

FILE_SIZE="$(du -h "$BACKUP_FILE" | cut -f1)"
echo "[$(date -Iseconds)] Backup completed successfully."
echo "  File: ${BACKUP_FILE}"
echo "  Size: ${FILE_SIZE}"
echo ""
echo "Retention recommendation: Keep daily backups for 30 days."
echo "  To clean old backups: find ${BACKUP_DIR} -name '*.sql' -mtime +30 -delete"
