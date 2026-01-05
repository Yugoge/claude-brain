#!/usr/bin/env bash
# Description: Create timestamped backup of review schedule
# Usage: scripts/review/backup-schedule.sh
# Exit codes: 0=success, 1=failure

set -euo pipefail

# Parameters
SCHEDULE_FILE="${1:-.review/schedule.json}"
BACKUP_DIR="${2:-.review/backups}"
MAX_BACKUPS="${3:-10}"

# Validate schedule file exists
if [[ ! -f "$SCHEDULE_FILE" ]]; then
  echo "Error: Schedule file not found: $SCHEDULE_FILE" >&2
  exit 1
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create timestamped backup
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="$BACKUP_DIR/schedule-$TIMESTAMP.json"

# Copy schedule to backup
cp "$SCHEDULE_FILE" "$BACKUP_FILE"

echo "✅ Backup created: $BACKUP_FILE"

# Rotate old backups (keep only MAX_BACKUPS most recent)
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/schedule-*.json 2>/dev/null | wc -l)

if [[ $BACKUP_COUNT -gt $MAX_BACKUPS ]]; then
  # Delete oldest backups
  DELETE_COUNT=$((BACKUP_COUNT - MAX_BACKUPS))
  ls -1t "$BACKUP_DIR"/schedule-*.json | tail -n "$DELETE_COUNT" | xargs rm -f
  echo "🗑️  Rotated: Deleted $DELETE_COUNT old backup(s)"
fi

exit 0
