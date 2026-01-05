#!/usr/bin/env python3
"""
Migrate Orphaned Rem Entries in FSRS Schedule

One-time migration script to fix rem_id mismatches caused by file renames
in commit adfc1c1 (2025-11-10). Updates schedule.json rem_ids while preserving
all FSRS learning history.

Root Cause:
    Files were renamed with new rem_id values (added subdomain prefixes like
    'finance-', 'fx-', 'derivatives-'), but schedule.json was not updated,
    causing orphaned entries that don't match any actual Rem files.

Solution:
    1. Detect orphaned schedule entries (rem_id not found in any Rem file)
    2. Scan knowledge-base for files matching domain/pattern
    3. Extract new rem_id from frontmatter
    4. Update schedule entry key while preserving FSRS history
    5. Create backup before modifying

Usage:
    python3 scripts/review/migrate-orphaned-rems.py [options]

Options:
    --dry-run           Preview changes without writing
    --yes               Auto-confirm prompts
    --verbose           Show detailed matching logic
    --mapping-file FILE JSON file with old→new rem_id mappings (optional)

Examples:
    # Preview migration
    python3 scripts/review/migrate-orphaned-rems.py --dry-run

    # Execute migration (interactive)
    python3 scripts/review/migrate-orphaned-rems.py

    # Auto-confirm migration
    python3 scripts/review/migrate-orphaned-rems.py --yes

Git Context:
    Root cause commit: adfc1c1 (2025-11-10)
    "fix: Restore misplaced scripts and align Rem filenames with rem_ids"

    Issue: Files renamed to match new rem_id values, but schedule.json
    retained old rem_ids, creating orphaned entries.
"""

import json
import argparse
import sys
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Set

# Project root
ROOT = Path(__file__).parent.parent.parent
KB_DIR = ROOT / "knowledge-base"
SCHEDULE_PATH = ROOT / ".review" / "schedule.json"

# Add scripts to path for imports
sys.path.append(str(ROOT / "scripts"))

from utils.file_lock import safe_write_json, safe_read_json


def extract_frontmatter(file_path: Path) -> Optional[Dict]:
    """
    Extract YAML frontmatter from Rem file.

    Returns:
        Dict with frontmatter fields, or None if no frontmatter
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract frontmatter (between --- markers)
        match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not match:
            return None

        frontmatter_text = match.group(1)

        # Simple YAML parser (key: value)
        frontmatter = {}
        for line in frontmatter_text.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Handle "key: value" format
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()

                # Remove quotes
                if value.startswith('"') or value.startswith("'"):
                    value = value[1:-1]

                frontmatter[key] = value

        return frontmatter if frontmatter else None

    except Exception as e:
        print(f"⚠️  Error reading {file_path}: {e}")
        return None


def detect_domain(file_path: Path) -> str:
    """
    Detect domain from file path using full directory hierarchy.

    Returns the complete relative path from knowledge-base to the file's directory.
    """
    relative_path = file_path.relative_to(KB_DIR)
    # Return the directory path (exclude filename)
    domain_parts = relative_path.parts[:-1]  # Remove filename

    if domain_parts:
        return '/'.join(domain_parts)
    return "general"


def find_all_rem_ids() -> Dict[str, Tuple[Path, str]]:
    """
    Scan knowledge-base and build mapping of rem_id → (file_path, domain).

    Returns:
        Dictionary mapping rem_id to (file_path, domain) tuple
    """
    rem_id_map = {}

    for md_file in KB_DIR.rglob('*.md'):
        # Skip templates and indexes
        if '_templates' in md_file.parts or '_index' in md_file.parts:
            continue

        # Skip hidden files
        if md_file.name.startswith('.'):
            continue

        frontmatter = extract_frontmatter(md_file)
        if not frontmatter or 'rem_id' not in frontmatter:
            continue

        rem_id = frontmatter['rem_id']
        domain = detect_domain(md_file)

        rem_id_map[rem_id] = (md_file, domain)

    return rem_id_map


def find_orphaned_entries(schedule: Dict, rem_id_map: Dict[str, Tuple[Path, str]]) -> List[str]:
    """
    Find schedule entries whose rem_id doesn't exist in any Rem file.

    Args:
        schedule: Loaded schedule.json data
        rem_id_map: Mapping of rem_id → (file_path, domain)

    Returns:
        List of orphaned rem_ids
    """
    orphaned = []

    for rem_id in schedule.get('concepts', {}).keys():
        if rem_id not in rem_id_map:
            orphaned.append(rem_id)

    return orphaned


def match_orphaned_to_files(
    orphaned: List[str],
    rem_id_map: Dict[str, Tuple[Path, str]],
    verbose: bool = False
) -> Dict[str, str]:
    """
    Match orphaned rem_ids to actual files using pattern analysis.

    Matching strategy:
    1. Domain matching (from schedule entry)
    2. Pattern analysis (detect added/removed prefixes)
    3. Levenshtein distance for fuzzy matching

    Args:
        orphaned: List of orphaned rem_ids
        rem_id_map: Mapping of rem_id → (file_path, domain)
        verbose: Show detailed matching logic

    Returns:
        Dictionary mapping old_rem_id → new_rem_id
    """
    mappings = {}

    # Load schedule to get domain info
    schedule = safe_read_json(SCHEDULE_PATH)

    for old_rem_id in orphaned:
        entry = schedule['concepts'][old_rem_id]
        entry_domain = entry.get('domain', '')

        if verbose:
            print(f"\n🔍 Matching orphaned entry: {old_rem_id}")
            print(f"   Domain: {entry_domain}")

        # Find candidates: files in same domain
        candidates = []
        for new_rem_id, (file_path, file_domain) in rem_id_map.items():
            # Domain must match (use ISCED path component for matching)
            # Extract ISCED path (e.g., '04-business-administration-and-law/...')
            if entry_domain and file_domain:
                # Check if ISCED paths overlap (flexible matching)
                entry_isced = entry_domain.split('/')[0] if '/' in entry_domain else entry_domain
                file_isced = file_domain.split('/')[0] if '/' in file_domain else file_domain

                if entry_isced != file_isced:
                    continue

            # Pattern matching: check if old_rem_id is substring of new_rem_id
            # or vice versa (handles added/removed prefixes)
            old_parts = set(old_rem_id.split('-'))
            new_parts = set(new_rem_id.split('-'))

            # Calculate overlap
            common_parts = old_parts & new_parts
            overlap_ratio = len(common_parts) / max(len(old_parts), len(new_parts))

            if overlap_ratio >= 0.6:  # At least 60% overlap
                candidates.append((new_rem_id, overlap_ratio, file_path))

        if not candidates:
            if verbose:
                print(f"   ❌ No candidates found")
            continue

        # Sort by overlap ratio (descending)
        candidates.sort(key=lambda x: x[1], reverse=True)

        best_match = candidates[0]
        new_rem_id, overlap, file_path = best_match

        if verbose:
            print(f"   ✅ Best match: {new_rem_id} (overlap: {overlap:.1%})")
            print(f"      File: {file_path.relative_to(ROOT)}")

        mappings[old_rem_id] = new_rem_id

    return mappings


def migrate_schedule_entries(
    mappings: Dict[str, str],
    dry_run: bool = False,
    verbose: bool = False
) -> int:
    """
    Migrate orphaned schedule entries to new rem_ids.

    CRITICAL: Preserve ALL FSRS history during migration:
    - difficulty
    - stability
    - retrievability
    - interval
    - next_review
    - last_review
    - review_count
    - created

    Only update: rem_id (key), domain, title, last_modified

    Args:
        mappings: Dictionary mapping old_rem_id → new_rem_id
        dry_run: Preview changes without writing
        verbose: Show detailed operations

    Returns:
        Number of entries migrated
    """
    if not mappings:
        print("❌ No mappings to migrate")
        return 0

    # Load schedule
    schedule = safe_read_json(SCHEDULE_PATH)

    # Create backup before modifying
    if not dry_run:
        import subprocess
        backup_script = ROOT / "scripts" / "review" / "backup-schedule.sh"
        if backup_script.exists():
            try:
                result = subprocess.run(
                    ['bash', str(backup_script)],
                    capture_output=True,
                    text=True,
                    cwd=str(ROOT)
                )
                if result.returncode == 0:
                    output = result.stdout.strip()
                    print(f"📦 {output}")
            except Exception as e:
                print(f"⚠️  Backup failed (continuing anyway): {e}")

    # Load rem_id_map to get updated metadata
    rem_id_map = find_all_rem_ids()

    migrated_count = 0

    for old_rem_id, new_rem_id in mappings.items():
        if old_rem_id not in schedule['concepts']:
            print(f"⚠️  Skipping {old_rem_id}: not in schedule")
            continue

        # Get existing entry (preserve FSRS history)
        old_entry = schedule['concepts'][old_rem_id]

        # Get new file metadata
        if new_rem_id not in rem_id_map:
            print(f"⚠️  Skipping {old_rem_id}: new rem_id {new_rem_id} not found")
            continue

        file_path, domain = rem_id_map[new_rem_id]
        frontmatter = extract_frontmatter(file_path)
        title = frontmatter.get('title', new_rem_id) if frontmatter else new_rem_id

        # Create updated entry (preserve FSRS history)
        new_entry = old_entry.copy()
        new_entry['id'] = new_rem_id
        new_entry['domain'] = domain
        new_entry['title'] = title
        new_entry['last_modified'] = datetime.now().strftime("%Y-%m-%d")

        if verbose:
            print(f"\n📝 Migrating: {old_rem_id} → {new_rem_id}")
            print(f"   Domain: {domain}")
            print(f"   Title: {title}")
            if 'fsrs_state' in old_entry:
                fsrs = old_entry['fsrs_state']
                print(f"   FSRS: D={fsrs['difficulty']:.2f}, S={fsrs['stability']:.2f}, reviews={fsrs['review_count']}")

        if not dry_run:
            # Add new entry
            schedule['concepts'][new_rem_id] = new_entry

            # Remove old entry
            del schedule['concepts'][old_rem_id]

        migrated_count += 1

    # Save updated schedule
    if not dry_run:
        safe_write_json(SCHEDULE_PATH, schedule, indent=2)
        print(f"\n✅ Schedule saved: {SCHEDULE_PATH}")

    return migrated_count


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Migrate orphaned Rem entries in FSRS schedule',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without writing')
    parser.add_argument('--yes', '-y', action='store_true',
                        help='Auto-confirm prompts')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show detailed matching logic')
    parser.add_argument('--mapping-file', type=str,
                        help='JSON file with old→new rem_id mappings (optional)')

    args = parser.parse_args()

    print("🔍 Scanning knowledge base for Rem files...")
    rem_id_map = find_all_rem_ids()
    print(f"✅ Found {len(rem_id_map)} Rem files")

    print("\n📖 Loading schedule...")
    schedule = safe_read_json(SCHEDULE_PATH)
    total_entries = len(schedule.get('concepts', {}))
    print(f"✅ Schedule contains {total_entries} entries")

    print("\n🔍 Detecting orphaned entries...")
    orphaned = find_orphaned_entries(schedule, rem_id_map)

    if not orphaned:
        print("✅ No orphaned entries found!")
        return 0

    print(f"⚠️  Found {len(orphaned)} orphaned entries:")
    for rem_id in orphaned:
        entry = schedule['concepts'][rem_id]
        domain = entry.get('domain', 'unknown')
        print(f"  - {rem_id} (domain: {domain})")

    # Load or generate mappings
    if args.mapping_file:
        print(f"\n📖 Loading mappings from {args.mapping_file}...")
        with open(args.mapping_file, 'r') as f:
            mappings = json.load(f)
    else:
        print("\n🔍 Auto-detecting file matches...")
        mappings = match_orphaned_to_files(orphaned, rem_id_map, args.verbose)

    if not mappings:
        print("❌ No matches found. Cannot proceed with migration.")
        print("   Consider creating a manual mapping file with --mapping-file")
        return 1

    print(f"\n📊 Migration Plan:")
    print(f"  Orphaned entries: {len(orphaned)}")
    print(f"  Matched entries: {len(mappings)}")
    print(f"  Unmatched entries: {len(orphaned) - len(mappings)}")

    print("\n🔄 Proposed migrations:")
    for old_rem_id, new_rem_id in mappings.items():
        entry = schedule['concepts'][old_rem_id]
        fsrs_info = ""
        if 'fsrs_state' in entry:
            fsrs = entry['fsrs_state']
            fsrs_info = f" (FSRS: D={fsrs['difficulty']:.2f}, reviews={fsrs['review_count']})"
        print(f"  {old_rem_id}")
        print(f"    → {new_rem_id}{fsrs_info}")

    # Confirm migration
    if not args.dry_run:
        print("\n⚠️  This will update schedule.json with new rem_ids")
        print("   ✅ FSRS history will be PRESERVED (difficulty, stability, review_count)")
        print("   🔄 Only rem_id, domain, title will be updated")

        if args.yes:
            print("\n✅ Auto-confirming")
        else:
            response = input("\nProceed with migration? (yes/no): ").strip().lower()
            if response != 'yes':
                print("❌ Cancelled by user")
                return 0

    # Execute migration
    migrated_count = migrate_schedule_entries(mappings, args.dry_run, args.verbose)

    if args.dry_run:
        print(f"\n[DRY RUN] Would migrate {migrated_count} entries")
        print("   Run without --dry-run to apply changes")
    else:
        print(f"\n✅ Successfully migrated {migrated_count} entries!")
        print(f"   Schedule updated: {SCHEDULE_PATH}")

        if len(orphaned) > len(mappings):
            unmatched = len(orphaned) - len(mappings)
            print(f"\n⚠️  {unmatched} orphaned entries could not be matched")
            print("   Review these entries manually:")
            for rem_id in orphaned:
                if rem_id not in mappings:
                    print(f"    - {rem_id}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
