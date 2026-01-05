#!/usr/bin/env python3
"""
Validate Review Schedule Integrity

Validates .review/schedule.json for common data integrity issues:
- Empty concepts dictionary
- Invalid date formats
- Missing required fields
- Orphaned entries (schedule entries without files)

Usage:
    source venv/bin/activate && python scripts/review/validate-schedule.py [--fix]

Options:
    --fix       Automatically fix issues where possible
    --verbose   Show detailed validation output

Exit codes:
    0 - Validation passed
    1 - Validation failed (issues found)
    2 - Critical error (cannot read schedule)
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import argparse

# Project root
ROOT = Path(__file__).parent.parent.parent
SCHEDULE_PATH = ROOT / ".review" / "schedule.json"
KB_DIR = ROOT / "knowledge-base"


def validate_date_format(date_str: str) -> bool:
    """Validate date is in YYYY-MM-DD format."""
    if not date_str:
        return False
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def find_rem_file(rem_id: str, domain: str) -> Path:
    """
    Find Rem file by searching knowledge base.
    Returns Path if found, None otherwise.
    """
    kb_root = Path(KB_DIR)

    # Pattern priority:
    # 1. Exact match with optional numeric prefix: NNN-{rem_id}.md
    # 2. Exact match without prefix: {rem_id}.md
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


def validate_schedule(schedule_path: Path, verbose: bool = False) -> dict:
    """
    Validate schedule.json integrity.

    Returns dict with validation results:
        {
            'valid': bool,
            'errors': list of error messages,
            'warnings': list of warning messages,
            'stats': dict with counts
        }
    """
    results = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'stats': {
            'total_concepts': 0,
            'invalid_dates': 0,
            'missing_fields': 0,
            'orphaned_entries': 0
        }
    }

    # Step 1: Check file exists
    if not schedule_path.exists():
        results['valid'] = False
        results['errors'].append(f"Schedule file not found: {schedule_path}")
        return results

    # Step 2: Load and parse JSON
    try:
        with open(schedule_path, 'r', encoding='utf-8') as f:
            schedule = json.load(f)
    except json.JSONDecodeError as e:
        results['valid'] = False
        results['errors'].append(f"Invalid JSON: {e}")
        return results
    except Exception as e:
        results['valid'] = False
        results['errors'].append(f"Cannot read schedule: {e}")
        return results

    # Step 3: Check concepts dictionary exists and not empty
    concepts = schedule.get('concepts', {})
    if not concepts:
        results['valid'] = False
        results['errors'].append("CRITICAL: concepts dictionary is empty")
        return results

    if not isinstance(concepts, dict):
        results['valid'] = False
        results['errors'].append(f"concepts must be a dictionary, got {type(concepts)}")
        return results

    results['stats']['total_concepts'] = len(concepts)

    # Step 4: Validate each concept entry
    required_fields = ['id', 'domain', 'title', 'active_algorithm', 'fsrs_state']
    fsrs_required_fields = ['difficulty', 'stability', 'next_review', 'review_count']

    orphaned = []

    for rem_id, rem_data in concepts.items():
        # Check required fields
        for field in required_fields:
            if field not in rem_data:
                results['errors'].append(f"{rem_id}: missing required field '{field}'")
                results['stats']['missing_fields'] += 1
                results['valid'] = False

        # Check FSRS state
        if 'fsrs_state' in rem_data:
            fsrs_state = rem_data['fsrs_state']
            for field in fsrs_required_fields:
                if field not in fsrs_state:
                    results['errors'].append(f"{rem_id}: missing FSRS field '{field}'")
                    results['stats']['missing_fields'] += 1
                    results['valid'] = False

            # Validate date format
            next_review = fsrs_state.get('next_review')
            if next_review and not validate_date_format(next_review):
                results['errors'].append(f"{rem_id}: invalid date format '{next_review}' (expected YYYY-MM-DD)")
                results['stats']['invalid_dates'] += 1
                results['valid'] = False

        # Check file exists
        domain = rem_data.get('domain', '')
        rem_file = find_rem_file(rem_id, domain)
        if not rem_file or not rem_file.exists():
            orphaned.append({
                'id': rem_id,
                'title': rem_data.get('title', rem_id),
                'domain': domain,
                'next_review': rem_data.get('fsrs_state', {}).get('next_review', 'unknown')
            })
            results['stats']['orphaned_entries'] += 1

    # Report orphaned entries as warnings (not errors)
    if orphaned:
        results['warnings'].append(f"Found {len(orphaned)} orphaned schedule entries (files missing)")
        if verbose:
            for entry in orphaned[:5]:
                results['warnings'].append(f"  - {entry['id']} (domain: {entry['domain']}, next: {entry['next_review']})")
            if len(orphaned) > 5:
                results['warnings'].append(f"  ... and {len(orphaned) - 5} more")

    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Validate review schedule integrity',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--fix', action='store_true',
                        help='Automatically fix issues where possible')
    parser.add_argument('--verbose', action='store_true',
                        help='Show detailed validation output')

    args = parser.parse_args()

    print(f"🔍 Validating schedule: {SCHEDULE_PATH}")

    results = validate_schedule(SCHEDULE_PATH, verbose=args.verbose)

    # Display results
    print(f"\n📊 Validation Results:")
    print(f"  Total concepts: {results['stats']['total_concepts']}")
    print(f"  Invalid dates: {results['stats']['invalid_dates']}")
    print(f"  Missing fields: {results['stats']['missing_fields']}")
    print(f"  Orphaned entries: {results['stats']['orphaned_entries']}")

    if results['errors']:
        print(f"\n❌ Errors ({len(results['errors'])}):")
        for error in results['errors']:
            print(f"  - {error}")

    if results['warnings']:
        print(f"\n⚠️  Warnings ({len(results['warnings'])}):")
        for warning in results['warnings']:
            print(f"  - {warning}")

    if results['valid']:
        print("\n✅ Validation passed!")
        return 0
    else:
        print("\n❌ Validation failed!")
        if args.fix:
            print("\n💡 Fix mode not yet implemented (would require backup + repair logic)")
        else:
            print("\n💡 Tip: Run with --fix to attempt automatic repairs")
        return 1


if __name__ == '__main__':
    sys.exit(main())
