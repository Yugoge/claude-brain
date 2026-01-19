#!/usr/bin/env python3
"""
Scan and Populate Rems to Review Schedule

Recursively scans knowledge-base for all Rem files (*.md with rem_id frontmatter)
and adds them to .review/schedule.json with initial FSRS state.

This script addresses Phase 3 requirement: Review ALL Rems, not just concepts/.

Usage:
    source venv/bin/activate && source venv/bin/activate && python3 scripts/scan-and-populate-rems.py [options]

Options:
    --domain DOMAIN       Only add Rems from specific domain
    --dry-run            Preview what would be added without writing
    --force              Add all Rems (reset existing)
    --verbose            Show detailed output
    --initial-date DATE  Set initial review date (YYYY-MM-DD, default: tomorrow)
    --algorithm ALGO     Use 'fsrs' or 'sm2' (default: fsrs)

Examples:
    # Add all Rems using FSRS
    source venv/bin/activate && source venv/bin/activate && python3 scripts/scan-and-populate-rems.py

    # Preview only
    source venv/bin/activate && source venv/bin/activate && python3 scripts/scan-and-populate-rems.py --dry-run

    # Add only finance Rems
    source venv/bin/activate && source venv/bin/activate && python3 scripts/scan-and-populate-rems.py --domain finance

    # Force re-add all Rems
    source venv/bin/activate && source venv/bin/activate && python3 scripts/scan-and-populate-rems.py --force
"""

import json
import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Set, Optional
import re

# Project root
ROOT = Path(__file__).parent.parent.parent  # Go up to knowledge-system root
KB_DIR = ROOT / "knowledge-base"
SCHEDULE_PATH = ROOT / ".review" / "schedule.json"

# Add scripts to path for imports
sys.path.append(str(ROOT / "scripts" / "review"))
sys.path.append(str(ROOT / "scripts"))

from fsrs_algorithm import FSRSAlgorithm
from utils.file_lock import safe_write_json, safe_read_json

# FSRS defaults
FSRS_DEFAULTS = {
    "desired_retention": 0.9,
    "maximum_interval": 36500
}

# SM-2 defaults (legacy)
SM2_DEFAULTS = {
    "initial_easiness_factor": 2.5,
    "initial_interval": 1,
    "initial_repetitions": 0,
    "min_easiness_factor": 1.3,
    "passing_grade": 3
}


def load_schedule() -> Dict:
    """
    Load existing schedule or create empty one.

    Uses safe_read_json with file locking to prevent reading during writes.
    """
    default_schedule = {
        "version": "2.0.0",
        "default_algorithm": "fsrs",
        "description": "FSRS-based spaced repetition schedule for all Rems",
        "concepts": {},
        "metadata": {
            "last_review": None,
            "total_reviews": 0,
            "concepts_due_today": 0,
            "algorithm_counts": {
                "fsrs": 0,
                "sm2": 0
            }
        },
        "fsrs_defaults": FSRS_DEFAULTS,
        "sm2_defaults": SM2_DEFAULTS
    }

    if not SCHEDULE_PATH.exists():
        return default_schedule

    # Use safe_read_json with file locking
    schedule = safe_read_json(SCHEDULE_PATH, default=default_schedule)

    # Upgrade old schema if needed
    if schedule.get("algorithm") == "SM-2":
        schedule["version"] = "2.0.0"
        schedule["default_algorithm"] = "fsrs"
        schedule["fsrs_defaults"] = FSRS_DEFAULTS

    return schedule


def save_schedule(schedule: Dict, dry_run: bool = False):
    """
    Save schedule atomically with file locking and validation.

    Uses safe_write_json to prevent concurrent write conflicts.
    Validates data integrity before writing to prevent data loss.
    Creates automatic backup before saving.
    """
    if dry_run:
        print(f"\n[DRY RUN] Would write to: {SCHEDULE_PATH}")
        return

    # Validation: Ensure concepts dict is not empty
    concepts = schedule.get('concepts', {})
    if not concepts or len(concepts) == 0:
        raise ValueError(
            "CRITICAL: Refusing to save empty schedule.json!\n"
            "  This would cause data loss. Check your data source.\n"
            "  If you need to clear the schedule, delete .review/schedule.json manually."
        )

    # Validation: Ensure concepts is a dictionary
    if not isinstance(concepts, dict):
        raise ValueError(
            f"CRITICAL: concepts must be a dictionary, got {type(concepts)}\n"
            "  Data corruption detected. Aborting save."
        )

    print(f"\n✅ Validation passed: {len(concepts)} concepts ready to save")

    SCHEDULE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Create automatic backup before save
    if SCHEDULE_PATH.exists():
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
                    # Extract backup filename from output
                    output = result.stdout.strip()
                    print(f"📦 {output}")
            except Exception as e:
                print(f"⚠️  Backup failed (continuing anyway): {e}")

    # Use safe_write_json with file locking and atomic write
    try:
        safe_write_json(SCHEDULE_PATH, schedule, indent=2)
        print(f"✅ Schedule saved: {SCHEDULE_PATH}")
    except TimeoutError as e:
        print(f"\n❌ Failed to save schedule: {e}")
        print("   Another process may be accessing the file. Try again in a moment.")
        raise


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

                # Parse arrays (simple)
                if value.startswith('['):
                    value = [v.strip() for v in value[1:-1].split(',')]

                frontmatter[key] = value

        return frontmatter if frontmatter else None

    except Exception as e:
        print(f"⚠️  Error reading {file_path}: {e}")
        return None


def extract_markdown_title(file_path: Path) -> Optional[str]:
    """
    Extract title from first Markdown heading (# ...) in Rem file.

    Returns:
        Title string (without # prefix), or None if not found
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Skip frontmatter (between --- markers)
        content_without_fm = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)

        # Find first level-1 heading (# Title)
        match = re.search(r'^#\s+(.+)$', content_without_fm, re.MULTILINE)
        if match:
            return match.group(1).strip()

        return None

    except Exception as e:
        print(f"⚠️  Error extracting title from {file_path}: {e}")
        return None


def is_reviewable_rem(file_path: Path, frontmatter: Dict) -> bool:
    """
    Determine if a Rem file should be added to review schedule.

    Criteria:
    - Must have rem_id in frontmatter
    - Must not be in _templates/ or _index/
    - Optional: reviewable: true (default true if not specified)
    """
    # Skip templates and indexes
    if '_templates' in file_path.parts or '_index' in file_path.parts:
        return False

    # Skip hidden files
    if file_path.name.startswith('.'):
        return False

    # Must have rem_id
    if 'rem_id' not in frontmatter:
        return False

    # Check reviewable flag (default: true)
    reviewable = frontmatter.get('reviewable', 'true')
    if isinstance(reviewable, str):
        reviewable = reviewable.lower() in ('true', 'yes', '1')

    return reviewable


def detect_domain(file_path: Path) -> str:
    """
    Detect domain from file path using full directory hierarchy.

    Returns the complete relative path from knowledge-base to the file's directory.

    Examples:
        knowledge-base/02-arts-and-humanities/023-languages/0231-language-acquisition/file.md
        → 02-arts-and-humanities/023-languages/0231-language-acquisition

        knowledge-base/04-business-administration-and-law/041-business-and-administration/0412-finance-banking-insurance/file.md
        → 04-business-administration-and-law/041-business-and-administration/0412-finance-banking-insurance
    """
    relative_path = file_path.relative_to(KB_DIR)
    # Return the directory path (exclude filename)
    domain_parts = relative_path.parts[:-1]  # Remove filename

    if domain_parts:
        return '/'.join(domain_parts)
    return "general"


def find_all_rems(domain_filter: Optional[str] = None) -> List[tuple]:
    """
    Recursively find all reviewable Rem files in knowledge base.

    Args:
        domain_filter: Optional domain to filter by

    Returns:
        List of (domain, rem_id, file_path, frontmatter, title) tuples
        where title is extracted from Markdown heading (# ...)
    """
    rems = []

    # Recursively scan all .md files
    for md_file in KB_DIR.rglob('*.md'):
        frontmatter = extract_frontmatter(md_file)
        if not frontmatter:
            continue

        if not is_reviewable_rem(md_file, frontmatter):
            continue

        domain = detect_domain(md_file)

        # Apply domain filter if specified
        if domain_filter and domain != domain_filter:
            continue

        rem_id = frontmatter['rem_id']

        # Extract title from Markdown heading (# ...)
        # Fallback chain: frontmatter title → Markdown heading → rem_id
        title = frontmatter.get('title') or extract_markdown_title(md_file) or rem_id

        rems.append((domain, rem_id, md_file, frontmatter, title))

    return rems


def create_initial_fsrs_state(rem_id: str, domain: str = "general", title: str = None, initial_date: Optional[str] = None, source: Optional[str] = None) -> Dict:
    """Create initial FSRS entry for a Rem."""
    fsrs = FSRSAlgorithm()

    if initial_date:
        next_review = datetime.strptime(initial_date, "%Y-%m-%d")
    else:
        next_review = datetime.now(timezone.utc) + timedelta(days=1)

    # Initial FSRS state (first review, assume "Good" rating = 3)
    initial_rating = 3
    initial_difficulty = fsrs.initial_difficulty(initial_rating)
    initial_stability = fsrs.initial_stability(initial_rating)

    entry = {
        "id": rem_id,
        "domain": domain,  # ADDED: Required for review grouping
        "title": title or rem_id,  # ADDED: Display name for the Rem
        "active_algorithm": "fsrs",
        "fsrs_state": {
            "difficulty": initial_difficulty,
            "stability": initial_stability,
            "retrievability": 1.0,  # Not reviewed yet
            "interval": int(initial_stability),
            "next_review": next_review.strftime("%Y-%m-%d"),
            "last_review": None,
            "review_count": 0
        },
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "last_modified": datetime.now(timezone.utc).strftime("%Y-%m-%d")
    }

    # Add source field if provided (conversation path for review-master context)
    if source:
        entry["source"] = source

    return entry


def create_initial_sm2_state(rem_id: str, domain: str = "general", title: str = None, initial_date: Optional[str] = None, source: Optional[str] = None) -> Dict:
    """Create initial SM-2 entry for a Rem (legacy support)."""
    if initial_date:
        next_review = datetime.strptime(initial_date, "%Y-%m-%d")
    else:
        next_review = datetime.now(timezone.utc) + timedelta(days=1)

    entry = {
        "id": rem_id,
        "domain": domain,  # ADDED: Required for review grouping
        "title": title or rem_id,  # ADDED: Display name for the Rem
        "active_algorithm": "sm2",
        "sm2_state": {
            "next_review_date": next_review.strftime("%Y-%m-%d"),
            "interval": SM2_DEFAULTS["initial_interval"],
            "easiness_factor": SM2_DEFAULTS["initial_easiness_factor"],
            "repetitions": SM2_DEFAULTS["initial_repetitions"],
            "last_reviewed": None
        },
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "last_modified": datetime.now(timezone.utc).strftime("%Y-%m-%d")
    }

    # Add source field if provided (conversation path for review-master context)
    if source:
        entry["source"] = source

    return entry


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Scan and populate review schedule from all Rem files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--domain', type=str,
                        help='Only add Rems from specific domain')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without writing')
    parser.add_argument('--force', action='store_true',
                        help='Add all Rems (reset existing)')
    parser.add_argument('--verbose', action='store_true',
                        help='Show detailed output')
    parser.add_argument('--initial-date', type=str,
                        help='Initial review date (YYYY-MM-DD, default: tomorrow)')
    parser.add_argument('--algorithm', type=str, default='fsrs',
                        choices=['fsrs', 'sm2'],
                        help='Scheduling algorithm (default: fsrs)')
    parser.add_argument('--yes', '-y', action='store_true',
                        help='Auto-confirm prompts')

    args = parser.parse_args()

    # Validate initial_date format if provided
    if args.initial_date:
        try:
            datetime.strptime(args.initial_date, "%Y-%m-%d")
        except ValueError:
            print(f"❌ Invalid date format: {args.initial_date}")
            print("   Expected: YYYY-MM-DD (e.g., 2025-11-01)")
            return 1

    print("🔍 Scanning knowledge base for Rem files...")
    print(f"📊 Algorithm: {args.algorithm.upper()}\n")

    # Find all Rems
    all_rems = find_all_rems(args.domain)

    if not all_rems:
        if args.domain:
            print(f"❌ No Rem files found in domain: {args.domain}")
        else:
            print("❌ No Rem files found in knowledge base")
        return 1

    print(f"✅ Found {len(all_rems)} reviewable Rem file(s)")

    # Group by domain for display
    by_domain = {}
    by_type = {}
    for domain, rem_id, file_path, frontmatter, title in all_rems:
        by_domain.setdefault(domain, []).append(rem_id)


    print("\n📂 Breakdown by domain:")
    for domain, rems in sorted(by_domain.items()):
        print(f"  - {domain}: {len(rems)} Rems")


    # Load existing schedule
    print(f"\n📖 Loading schedule from {SCHEDULE_PATH}...")
    schedule = load_schedule()
    existing_concepts = set(schedule.get('concepts', {}).keys())

    if existing_concepts:
        print(f"✅ Schedule contains {len(existing_concepts)} existing Rem(s)")
    else:
        print("📝 Schedule is empty (will be populated)")

    # Determine which Rems to add or update
    new_rems = []  # New Rems to add with initial state
    update_rems = []  # Existing Rems to update (preserve FSRS state)
    skipped_rems = []

    for domain, rem_id, file_path, frontmatter, title in all_rems:
        if rem_id in existing_concepts:
            if args.force:
                # PRESERVE existing FSRS state, only update metadata
                existing_entry = schedule['concepts'][rem_id]
                update_rems.append((domain, rem_id, file_path, frontmatter, title, existing_entry))
                if args.verbose:
                    print(f"  🔄 Will update {rem_id} (preserving FSRS history)")
            else:
                skipped_rems.append(rem_id)
                if args.verbose:
                    print(f"  ⏭️  Skipping {rem_id} (already in schedule)")
        else:
            # New Rem - create with initial state
            new_rems.append((domain, rem_id, file_path, frontmatter, title))
            if args.verbose:
                print(f"  ➕ Will add {rem_id} ({domain})")

    print(f"\n📊 Summary:")
    print(f"  - Rems to add (new): {len(new_rems)}")
    print(f"  - Rems to update (preserve history): {len(update_rems)}")
    print(f"  - Rems skipped: {len(skipped_rems)}")

    if not new_rems and not update_rems:
        print("\n✅ Nothing to do (all Rems already in schedule)")
        print("   Use --force to update metadata while preserving FSRS history")
        return 0

    # Confirm action
    if not args.dry_run:
        if new_rems:
            print(f"\n⚠️  This will add {len(new_rems)} NEW Rem(s) to review schedule using {args.algorithm.upper()}")
            if args.initial_date:
                print(f"   First review date: {args.initial_date}")
            else:
                tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                print(f"   First review date: {tomorrow} (tomorrow)")

        if update_rems:
            print(f"\n⚠️  This will update {len(update_rems)} EXISTING Rem(s) (preserving FSRS history)")
            print(f"   ✅ FSRS state will be PRESERVED (difficulty, stability, next_review)")
            print(f"   🔄 Only metadata will be updated (domain, title)")

        if args.yes:
            print("\n✅ Auto-confirming")
        else:
            response = input("\nProceed? (yes/no): ").strip().lower()
            if response != 'yes':
                print("❌ Cancelled by user")
                return 0

    # Add NEW Rems to schedule
    if new_rems:
        print(f"\n➕ Adding {len(new_rems)} NEW Rem(s) to schedule...")

        for domain, rem_id, file_path, frontmatter, title in new_rems:
            # title is already extracted from Markdown heading
            # Extract source field from frontmatter (conversation path for review-master)
            source = frontmatter.get('source')

            if args.algorithm == 'fsrs':
                rem_entry = create_initial_fsrs_state(rem_id, domain, title, args.initial_date, source)
            else:
                rem_entry = create_initial_sm2_state(rem_id, domain, title, args.initial_date, source)

            schedule['concepts'][rem_id] = rem_entry

            if args.verbose:
                if args.algorithm == 'fsrs':
                    next_date = rem_entry['fsrs_state']['next_review']
                else:
                    next_date = rem_entry['sm2_state']['next_review_date']
                source_info = f", source: {source}" if source else ""
                print(f"  ✅ Added {rem_id} (title: {title}, next review: {next_date}{source_info})")

    # Update EXISTING Rems (preserve FSRS state)
    if update_rems:
        print(f"\n🔄 Updating {len(update_rems)} EXISTING Rem(s) (preserving FSRS history)...")

        for domain, rem_id, file_path, frontmatter, title, existing_entry in update_rems:
            # title is already extracted from Markdown heading
            # Extract source field from frontmatter (conversation path for review-master)
            source = frontmatter.get('source')

            # PRESERVE all FSRS state data
            # Only update metadata fields
            schedule['concepts'][rem_id]['domain'] = domain
            schedule['concepts'][rem_id]['title'] = title
            schedule['concepts'][rem_id]['last_modified'] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            # Update source if present in frontmatter
            if source:
                schedule['concepts'][rem_id]['source'] = source
            elif 'source' in schedule['concepts'][rem_id]:
                # Remove source if no longer in frontmatter
                del schedule['concepts'][rem_id]['source']

            # DO NOT TOUCH:
            # - fsrs_state (difficulty, stability, retrievability, interval, next_review, review_count)
            # - created (original creation date)
            # - last_review (last review date)

            if args.verbose:
                if 'fsrs_state' in existing_entry:
                    next_date = existing_entry['fsrs_state']['next_review']
                    difficulty = existing_entry['fsrs_state']['difficulty']
                    review_count = existing_entry['fsrs_state']['review_count']
                    source_info = f", source: {source}" if source else ""
                    print(f"  ✅ Updated {rem_id} (title: {title}, next: {next_date}, D: {difficulty:.2f}, reviews: {review_count}{source_info})")
                else:
                    next_date = existing_entry['sm2_state']['next_review_date']
                    source_info = f", source: {source}" if source else ""
                    print(f"  ✅ Updated {rem_id} (title: {title}, next: {next_date}{source_info})")

    # Update metadata
    schedule['metadata']['concepts_due_today'] = len([
        r for r in schedule['concepts'].values()
        if r.get('fsrs_state', {}).get('next_review') == datetime.now().strftime("%Y-%m-%d")
    ])

    # Update algorithm counts
    algo_counts = {"fsrs": 0, "sm2": 0}
    for rem in schedule['concepts'].values():
        algo = rem.get('active_algorithm', 'fsrs')
        algo_counts[algo] = algo_counts.get(algo, 0) + 1
    schedule['metadata']['algorithm_counts'] = algo_counts

    # Save schedule
    save_schedule(schedule, args.dry_run)

    if args.dry_run:
        print("\n[DRY RUN] No changes were made")
    else:
        total_changes = len(new_rems) + len(update_rems)
        print(f"\n✅ Successfully processed {total_changes} Rem(s)!")
        print(f"   - New Rems added: {len(new_rems)}")
        print(f"   - Existing Rems updated: {len(update_rems)} (FSRS history preserved)")
        print(f"📊 Algorithm distribution: FSRS={algo_counts['fsrs']}, SM-2={algo_counts['sm2']}")

        # Show next steps
        print("\n📅 Next steps:")
        print("  1. Run '/review' to start reviewing Rems")
        print("  2. The system will show Rems due for review")
        print("  3. Review sessions update the schedule automatically")
        print(f"  4. FSRS will personalize to your performance over time")

        if update_rems:
            print("\n💡 Note: --force now PRESERVES your FSRS history!")
            print("   ✅ Your review progress (difficulty, stability, next_review) is safe")

    return 0


if __name__ == '__main__':
    sys.exit(main())
