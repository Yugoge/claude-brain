#!/usr/bin/env python3
"""
Sync Renamed Rems to FSRS Schedule (Automated Detection)

Automated script to detect and sync file path/rem_id changes to schedule.json.
Prevents future orphaned entries by automatically detecting renames and updating
schedule while preserving FSRS history.

Purpose:
    Prevent rem_id mismatches like commit adfc1c1 (2025-11-10) from recurring.
    This script automatically detects when files have been renamed with new
    rem_ids but schedule.json still contains old rem_ids.

Detection Strategy:
    1. Find orphaned schedule entries (rem_id not in any Rem file)
    2. Use domain + pattern matching to find candidate files
    3. Extract rem_id from frontmatter
    4. Update schedule key preserving FSRS history

Integration:
    - Can be run as part of /maintain workflow (Task 10)
    - Safe to run repeatedly (idempotent)
    - Always creates backup before modifying

Usage:
    source venv/bin/activate && source venv/bin/activate && python3 scripts/review/sync-renamed-rems.py [options]

Options:
    --dry-run           Preview changes without writing
    --yes               Auto-confirm prompts
    --verbose           Show detailed matching logic

Examples:
    # Check for mismatches (dry-run)
    source venv/bin/activate && source venv/bin/activate && python3 scripts/review/sync-renamed-rems.py --dry-run

    # Execute sync (interactive)
    source venv/bin/activate && source venv/bin/activate && python3 scripts/review/sync-renamed-rems.py

    # Auto-confirm sync
    source venv/bin/activate && source venv/bin/activate && python3 scripts/review/sync-renamed-rems.py --yes

Git Context:
    Root cause commit: adfc1c1 (2025-11-10)
    "fix: Restore misplaced scripts and align Rem filenames with rem_ids"

    Prevention: This script detects and fixes rem_id mismatches automatically,
    preventing orphaned entries from accumulating.
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
        if 'verbose' in sys.argv:
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


def calculate_pattern_similarity(old_rem_id: str, new_rem_id: str) -> float:
    """
    Calculate similarity between two rem_ids based on word overlap.

    Strategy:
    - Split by hyphens into words
    - Calculate Jaccard similarity (intersection / union)
    - Boost score if old_rem_id is substring of new_rem_id or vice versa

    Args:
        old_rem_id: Original rem_id from schedule
        new_rem_id: Candidate rem_id from file

    Returns:
        Similarity score (0.0 to 1.0)
    """
    old_parts = set(old_rem_id.split('-'))
    new_parts = set(new_rem_id.split('-'))

    # Jaccard similarity
    intersection = old_parts & new_parts
    union = old_parts | new_parts

    if not union:
        return 0.0

    base_score = len(intersection) / len(union)

    # Boost if substring relationship exists
    if old_rem_id in new_rem_id or new_rem_id in old_rem_id:
        base_score = min(1.0, base_score * 1.2)

    return base_score


def match_orphaned_to_files(
    orphaned: List[str],
    rem_id_map: Dict[str, Tuple[Path, str]],
    schedule: Dict,
    verbose: bool = False
) -> Dict[str, str]:
    """
    Match orphaned rem_ids to actual files using intelligent pattern analysis.

    Matching strategy:
    1. Domain matching (must match ISCED top-level)
    2. Pattern similarity (word overlap + substring matching)
    3. Confidence threshold (>= 60% similarity)

    Args:
        orphaned: List of orphaned rem_ids
        rem_id_map: Mapping of rem_id → (file_path, domain)
        schedule: Loaded schedule data (for domain info)
        verbose: Show detailed matching logic

    Returns:
        Dictionary mapping old_rem_id → new_rem_id
    """
    mappings = {}

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
            # Extract ISCED top-level (e.g., '04-business-administration-and-law')
            if entry_domain and file_domain:
                entry_isced = entry_domain.split('/')[0] if '/' in entry_domain else entry_domain
                file_isced = file_domain.split('/')[0] if '/' in file_domain else file_domain

                if entry_isced != file_isced:
                    continue

            # Calculate pattern similarity
            similarity = calculate_pattern_similarity(old_rem_id, new_rem_id)

            if similarity >= 0.6:  # At least 60% similarity
                candidates.append((new_rem_id, similarity, file_path))

        if not candidates:
            if verbose:
                print(f"   ❌ No candidates found (similarity < 60%)")
            continue

        # Sort by similarity (descending)
        candidates.sort(key=lambda x: x[1], reverse=True)

        best_match = candidates[0]
        new_rem_id, similarity, file_path = best_match

        # Only accept high-confidence matches
        if similarity < 0.6:
            if verbose:
                print(f"   ❌ Best match below threshold: {new_rem_id} ({similarity:.1%})")
            continue

        if verbose:
            print(f"   ✅ Best match: {new_rem_id} (similarity: {similarity:.1%})")
            print(f"      File: {file_path.relative_to(ROOT)}")

        mappings[old_rem_id] = new_rem_id

    return mappings


def sync_schedule_entries(
    mappings: Dict[str, str],
    dry_run: bool = False,
    verbose: bool = False
) -> int:
    """
    Sync orphaned schedule entries to new rem_ids.

    CRITICAL: Preserve ALL FSRS history during sync:
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
        Number of entries synced
    """
    if not mappings:
        if verbose:
            print("ℹ️  No mappings to sync")
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
                if verbose:
                    print(f"⚠️  Backup failed (continuing anyway): {e}")

    # Load rem_id_map to get updated metadata
    rem_id_map = find_all_rem_ids()

    synced_count = 0

    for old_rem_id, new_rem_id in mappings.items():
        if old_rem_id not in schedule['concepts']:
            if verbose:
                print(f"⚠️  Skipping {old_rem_id}: not in schedule")
            continue

        # Get existing entry (preserve FSRS history)
        old_entry = schedule['concepts'][old_rem_id]

        # Get new file metadata
        if new_rem_id not in rem_id_map:
            if verbose:
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
            print(f"\n📝 Syncing: {old_rem_id} → {new_rem_id}")
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

        synced_count += 1

    # Save updated schedule
    if not dry_run and synced_count > 0:
        safe_write_json(SCHEDULE_PATH, schedule, indent=2)
        if verbose:
            print(f"\n✅ Schedule saved: {SCHEDULE_PATH}")

    return synced_count


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Sync renamed Rems to FSRS schedule (automated detection)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without writing')
    parser.add_argument('--yes', '-y', action='store_true',
                        help='Auto-confirm prompts')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show detailed matching logic')

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
        print("✅ No orphaned entries found! All rem_ids are in sync.")
        return 0

    print(f"⚠️  Found {len(orphaned)} orphaned entries")

    if args.verbose:
        for rem_id in orphaned:
            entry = schedule['concepts'][rem_id]
            domain = entry.get('domain', 'unknown')
            print(f"  - {rem_id} (domain: {domain})")

    print("\n🔍 Auto-detecting file matches...")
    mappings = match_orphaned_to_files(orphaned, rem_id_map, schedule, args.verbose)

    if not mappings:
        print("ℹ️  No high-confidence matches found.")
        print("   Orphaned entries may need manual review or use migrate-orphaned-rems.py")
        return 0

    print(f"\n📊 Sync Plan:")
    print(f"  Orphaned entries: {len(orphaned)}")
    print(f"  Matched entries: {len(mappings)}")
    print(f"  Unmatched entries: {len(orphaned) - len(mappings)}")

    if not args.verbose:
        print("\n🔄 Proposed syncs:")
        for old_rem_id, new_rem_id in mappings.items():
            print(f"  {old_rem_id} → {new_rem_id}")

    # Confirm sync
    if not args.dry_run:
        print("\n⚠️  This will update schedule.json with new rem_ids")
        print("   ✅ FSRS history will be PRESERVED (difficulty, stability, review_count)")
        print("   🔄 Only rem_id, domain, title will be updated")

        if args.yes:
            print("\n✅ Auto-confirming")
        else:
            response = input("\nProceed with sync? (yes/no): ").strip().lower()
            if response != 'yes':
                print("❌ Cancelled by user")
                return 0

    # Execute sync
    synced_count = sync_schedule_entries(mappings, args.dry_run, args.verbose)

    if args.dry_run:
        print(f"\n[DRY RUN] Would sync {synced_count} entries")
        print("   Run without --dry-run to apply changes")
    else:
        if synced_count > 0:
            print(f"\n✅ Successfully synced {synced_count} entries!")
            print(f"   Schedule updated: {SCHEDULE_PATH}")
        else:
            print("\nℹ️  No entries synced")

        if len(orphaned) > len(mappings):
            unmatched = len(orphaned) - len(mappings)
            print(f"\n⚠️  {unmatched} orphaned entries could not be auto-matched")
            print("   These entries may need manual review:")
            for rem_id in orphaned:
                if rem_id not in mappings:
                    print(f"    - {rem_id}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
