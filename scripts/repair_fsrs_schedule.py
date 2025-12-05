#!/usr/bin/env python3
"""
FSRS Schedule Repair Script - Add all missing rems to the review schedule.
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from glob import glob
import hashlib

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from review.fsrs_algorithm import FSRSAlgorithm

def get_rem_id_from_path(rem_path):
    """Extract rem ID from file path."""
    # Convert path to Path object
    p = Path(rem_path)

    # Get relative path from knowledge-base
    kb_path = Path("knowledge-base")
    try:
        rel_path = p.relative_to(kb_path)
    except ValueError:
        # If not under knowledge-base, use full path
        rel_path = p

    # Remove .md extension and convert to ID format
    rem_id = str(rel_path).replace('.md', '').replace('/', '-')

    # Special handling for concepts subdirectory
    if 'concepts' in str(rel_path):
        # Extract just the filename without concepts/ prefix
        rem_id = p.stem

    return rem_id

def init_fsrs_state():
    """Initialize FSRS state for a new concept."""
    # Initial state for a new concept before any reviews
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    initial_state = {
        "difficulty": 0.3,       # Default difficulty
        "stability": 1.0,        # Initial stability
        "elapsed_days": 0,       # Days since last review
        "scheduled_days": 1,     # Days until next review
        "reps": 0,              # Number of reviews
        "lapses": 0,            # Number of lapses (failures)
        "state": 0,             # Learning state (0=new, 1=learning, 2=review, 3=relearning)
        "next_review": tomorrow, # Next review date
        "last_review": None,    # Last review date
        "review_count": 0       # Total review count
    }

    return initial_state

def main():
    """Main repair function."""
    print("=" * 60)
    print("FSRS Schedule Repair - Adding All Missing Rems")
    print("=" * 60)

    # Load current schedule
    schedule_path = Path(".review/schedule.json")
    with open(schedule_path, 'r') as f:
        schedule = json.load(f)

    if 'concepts' not in schedule:
        schedule['concepts'] = {}

    initial_count = len(schedule['concepts'])
    print(f"Initial concepts in schedule: {initial_count}")

    # Find all rem files
    kb_path = Path("knowledge-base")

    # Get all .md files recursively, excluding _index and _taxonomy directories
    rem_files = []
    for md_file in kb_path.glob("**/*.md"):
        # Skip files in _index, _taxonomy, and _templates directories
        if any(part.startswith('_') for part in md_file.parts):
            continue
        rem_files.append(md_file)

    print(f"Total rem files found: {len(rem_files)}")

    # Track added rems
    added_count = 0
    skipped_count = 0

    # Process each rem file
    for rem_path in rem_files:
        # Get rem ID
        rem_id = get_rem_id_from_path(rem_path)

        # Check if already in schedule
        if rem_id in schedule['concepts']:
            skipped_count += 1
            continue

        # Check alternative ID formats
        # Try with full path structure
        alt_id = str(rem_path).replace('knowledge-base/', '').replace('.md', '').replace('/', '-')
        if alt_id in schedule['concepts']:
            skipped_count += 1
            continue

        # Try just the filename
        simple_id = rem_path.stem
        if simple_id in schedule['concepts']:
            skipped_count += 1
            continue

        # Add new concept to schedule
        print(f"  Adding: {rem_id} (from {rem_path})")

        schedule['concepts'][rem_id] = {
            'rem_id': rem_id,
            'path': str(rem_path),
            'active_algorithm': 'fsrs',
            'fsrs_state': init_fsrs_state(),
            'added_to_schedule': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        added_count += 1

    # Save updated schedule
    print(f"\nSummary:")
    print(f"  - Initial concepts: {initial_count}")
    print(f"  - Rems added: {added_count}")
    print(f"  - Rems skipped (already in schedule): {skipped_count}")
    print(f"  - Final concepts: {len(schedule['concepts'])}")

    # Backup and save
    if added_count > 0:
        # Create backup
        backup_path = schedule_path.with_suffix(f'.backup-repair-{datetime.now().strftime("%Y%m%d-%H%M%S")}.json')
        with open(backup_path, 'w') as f:
            json.dump(schedule, f, indent=2)
        print(f"\nBackup saved to: {backup_path}")

        # Save updated schedule
        with open(schedule_path, 'w') as f:
            json.dump(schedule, f, indent=2)
        print(f"Schedule updated successfully!")
    else:
        print("\nNo changes needed - all rems already in schedule")

    return added_count

if __name__ == "__main__":
    added = main()
    sys.exit(0 if added >= 0 else 1)