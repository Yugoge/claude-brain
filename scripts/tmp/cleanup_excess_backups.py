#!/usr/bin/env python3
"""
One-time cleanup script for excess backup files.

Cleans up backup files across the project, keeping only the most recent N backups.
"""

import sys
from pathlib import Path

def cleanup_old_backups(file_path: Path, keep_count: int = 5) -> int:
    """
    Remove old backup files, keeping only most recent N.

    Args:
        file_path: Original file path (backups have .backup-TIMESTAMP suffix)
        keep_count: Number of recent backups to keep

    Returns:
        Number of backups deleted
    """
    file_path = Path(file_path)
    backup_pattern = f"{file_path.name}.backup-*"

    # Sort by filename timestamp
    backups = sorted(
        file_path.parent.glob(backup_pattern),
        key=lambda p: p.name,
        reverse=True
    )

    deleted = 0
    for backup in backups[keep_count:]:
        try:
            backup.unlink()
            deleted += 1
        except Exception:
            pass

    return deleted

def main():
    root = Path("/home/user/knowledge-system")

    print("=" * 70)
    print("BACKUP CLEANUP REPORT")
    print("=" * 70)

    total_deleted = 0

    # Target files that have backups
    targets = [
        (root / "chats/index.json", 3),  # Keep last 3
        (root / "knowledge-base/_index/backlinks.json", 2),  # Keep last 2
    ]

    for target_file, keep_count in targets:
        if target_file.exists():
            deleted = cleanup_old_backups(target_file, keep_count=keep_count)
            if deleted > 0:
                print(f"\n✓ {target_file.name}")
                print(f"  Deleted: {deleted} old backup(s)")
                print(f"  Kept: {keep_count} recent backup(s)")
                total_deleted += deleted
            else:
                print(f"\n✓ {target_file.name}")
                print(f"  No cleanup needed (≤{keep_count} backups)")

    # Manual cleanup for .review/schedule.json.backup-rename-*
    review_backups = list(root.glob(".review/schedule.json.backup-rename-*"))
    if review_backups:
        for backup in review_backups:
            backup.unlink()
            print(f"\n✓ {backup.name}")
            print(f"  Deleted: Obsolete backup")
            total_deleted += len(review_backups)

    print("\n" + "=" * 70)
    print(f"TOTAL: Deleted {total_deleted} backup file(s)")
    print("=" * 70)

    return 0

if __name__ == '__main__':
    sys.exit(main())
