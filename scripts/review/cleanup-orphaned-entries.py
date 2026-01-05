#!/usr/bin/env python3
"""
Cleanup Orphaned Schedule Entries

Detects and removes schedule entries that have no corresponding Rem file.

This addresses the issue where schedule.json contains entries for Rems
whose files have been deleted, moved, or renamed.

Usage:
    source venv/bin/activate && python scripts/review/cleanup-orphaned-entries.py [options]

Options:
    --dry-run       Show what would be removed without making changes
    --yes           Skip confirmation prompt
    --backup        Create backup before cleanup (default: true)
    --no-backup     Skip backup creation

Exit codes:
    0 - Success (cleaned up or nothing to do)
    1 - Failure (errors during cleanup)
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import subprocess

# Project root
ROOT = Path(__file__).parent.parent.parent
SCHEDULE_PATH = ROOT / ".review" / "schedule.json"
KB_DIR = ROOT / "knowledge-base"

# Add scripts to path
sys.path.append(str(ROOT / "scripts"))
from utils.file_lock import safe_read_json, safe_write_json


def find_rem_file(rem_id: str, domain: str) -> Path:
    """
    Find Rem file by searching knowledge base.
    Returns Path if found, None otherwise.
    """
    kb_root = Path(KB_DIR)

    # Pattern priority:
    # 1. Exact match with optional numeric prefix: NNN-{rem_id}.md
    # 2. Exact match without prefix: {rem_id}.md
    # 3. Fuzzy match containing rem_id
    patterns = [
        f"**/*-{rem_id}.md",
        f"**/{rem_id}.md",
        f"**/*{rem_id}*.md",
    ]

    for pattern in patterns:
        matches = list(kb_root.glob(pattern))
        if matches:
            # Prefer domain match
            domain_matches = [m for m in matches if domain in str(m)]
            if domain_matches:
                return domain_matches[0]
            return matches[0]

    return None


def find_orphaned_entries(schedule: dict) -> list:
    """
    Find schedule entries with missing Rem files.

    Returns:
        List of (rem_id, rem_data) tuples for orphaned entries
    """
    orphaned = []
    concepts = schedule.get('concepts', {})

    for rem_id, rem_data in concepts.items():
        domain = rem_data.get('domain', '')
        rem_file = find_rem_file(rem_id, domain)

        if not rem_file or not rem_file.exists():
            orphaned.append((rem_id, rem_data))

    return orphaned


def create_backup(schedule_path: Path) -> bool:
    """Create backup using backup-schedule.sh script."""
    try:
        result = subprocess.run(
            ['bash', str(ROOT / 'scripts' / 'review' / 'backup-schedule.sh')],
            capture_output=True,
            text=True,
            cwd=str(ROOT)
        )
        if result.returncode == 0:
            print(f"✅ {result.stdout.strip()}")
            return True
        else:
            print(f"⚠️  Backup failed: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"⚠️  Backup failed: {e}")
        return False


def remove_orphaned_entries(schedule: dict, orphaned: list) -> dict:
    """
    Remove orphaned entries from schedule.

    Args:
        schedule: Full schedule dict
        orphaned: List of (rem_id, rem_data) tuples

    Returns:
        Updated schedule dict
    """
    for rem_id, _ in orphaned:
        del schedule['concepts'][rem_id]

    # Update metadata
    schedule['metadata']['last_modified'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return schedule


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Cleanup orphaned schedule entries',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be removed without making changes')
    parser.add_argument('--yes', '-y', action='store_true',
                        help='Skip confirmation prompt')
    parser.add_argument('--backup', dest='backup', action='store_true', default=True,
                        help='Create backup before cleanup (default)')
    parser.add_argument('--no-backup', dest='backup', action='store_false',
                        help='Skip backup creation')

    args = parser.parse_args()

    print(f"🔍 Scanning for orphaned entries in: {SCHEDULE_PATH}")

    # Step 1: Load schedule
    try:
        schedule = safe_read_json(SCHEDULE_PATH)
    except Exception as e:
        print(f"❌ Failed to load schedule: {e}")
        return 1

    total_concepts = len(schedule.get('concepts', {}))
    print(f"📊 Total concepts in schedule: {total_concepts}")

    # Step 2: Find orphaned entries
    orphaned = find_orphaned_entries(schedule)

    if not orphaned:
        print("✅ No orphaned entries found!")
        return 0

    # Step 3: Display orphaned entries
    print(f"\n⚠️  Found {len(orphaned)} orphaned entry/entries:")
    for rem_id, rem_data in orphaned[:10]:  # Show max 10
        title = rem_data.get('title', rem_id)
        domain = rem_data.get('domain', 'unknown')
        next_review = rem_data.get('fsrs_state', {}).get('next_review', 'unknown')
        print(f"  - {rem_id}")
        print(f"    Title: {title}")
        print(f"    Domain: {domain}")
        print(f"    Next review: {next_review}")

    if len(orphaned) > 10:
        print(f"  ... and {len(orphaned) - 10} more")

    # Step 4: Confirm removal
    if args.dry_run:
        print(f"\n[DRY RUN] Would remove {len(orphaned)} orphaned entry/entries")
        return 0

    if not args.yes:
        print(f"\n⚠️  This will remove {len(orphaned)} entry/entries from the schedule.")
        response = input("Proceed? (yes/no): ").strip().lower()
        if response != 'yes':
            print("❌ Cancelled by user")
            return 0

    # Step 5: Create backup
    if args.backup:
        print("\n📦 Creating backup...")
        if not create_backup(SCHEDULE_PATH):
            print("⚠️  Backup failed but continuing...")

    # Step 6: Remove orphaned entries
    print(f"\n🗑️  Removing {len(orphaned)} orphaned entry/entries...")
    updated_schedule = remove_orphaned_entries(schedule, orphaned)

    # Step 7: Save updated schedule
    try:
        safe_write_json(SCHEDULE_PATH, updated_schedule, indent=2)
        print(f"✅ Schedule updated: {SCHEDULE_PATH}")
        print(f"   Removed: {len(orphaned)} entries")
        print(f"   Remaining: {len(updated_schedule['concepts'])} concepts")
        return 0
    except Exception as e:
        print(f"❌ Failed to save schedule: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
