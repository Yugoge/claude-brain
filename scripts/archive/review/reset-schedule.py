#!/usr/bin/env python3
"""
Reset Schedule Script (NUCLEAR OPTION)

Resets SM-2 spaced repetition schedule for concepts. Use with extreme caution.
Creates backups before any modifications.

Usage:
    python3 scripts/reset-schedule.py [options]

Reset Options:
    --full-reset          Reset all concepts (requires confirmation)
    --reset-domain DOMAIN Reset only concepts in specific domain
    --reset-concept ID    Reset specific concept only
    --force               Skip confirmation prompts (for automation)

Common Options:
    --dry-run            Preview changes without writing
    --verbose            Enable DEBUG logging
    --quiet              Minimize output (warnings only)
    --backup-dir DIR     Custom backup directory
    --no-backup          Skip backup creation

Examples:
    # Full reset with confirmation
    python3 scripts/reset-schedule.py --full-reset

    # Reset specific domain
    python3 scripts/reset-schedule.py --reset-domain finance

    # Reset specific concept
    python3 scripts/reset-schedule.py --reset-concept option-delta-universal-definition

    # Force mode for automation (no prompts)
    python3 scripts/reset-schedule.py --full-reset --force

    # Preview reset
    python3 scripts/reset-schedule.py --full-reset --dry-run
"""

import json
import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

# Add scripts directory to path for imports
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from rebuild_utils import (
    create_backup,
    setup_logging,
    atomic_write_json,
    check_disk_space
)

# Constants
ROOT = Path(__file__).parent.parent
REVIEW_DIR = ROOT / ".review"
SCHEDULE_PATH = REVIEW_DIR / "schedule.json"
KB_DIR = ROOT / "knowledge-base"

# SM-2 defaults
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

    Returns:
        Schedule data structure
    """
    if not SCHEDULE_PATH.exists():
        return {
            "version": "1.0.0",
            "algorithm": "SM-2",
            "description": "Spaced repetition schedule for all learned concepts",
            "concepts": {},
            "metadata": {
                "last_review": None,
                "total_reviews": 0,
                "concepts_due_today": 0
            },
            "sm2_defaults": SM2_DEFAULTS
        }

    with open(SCHEDULE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_concept_domain(concept_id: str) -> Optional[str]:
    """
    Find domain for a concept ID by searching knowledge base.

    Args:
        concept_id: Concept identifier

    Returns:
        Domain name or None if not found
    """
    for domain_dir in KB_DIR.iterdir():
        if not domain_dir.is_dir() or domain_dir.name.startswith('_'):
            continue

        concepts_dir = domain_dir / "concepts"
        if not concepts_dir.exists():
            continue

        # Check if concept file exists in this domain
        concept_file = concepts_dir / f"{concept_id}.md"
        if concept_file.exists():
            return domain_dir.name

    return None


def get_concepts_by_domain(domain: str) -> List[str]:
    """
    Get all concept IDs for a domain.

    Args:
        domain: Domain name

    Returns:
        List of concept IDs
    """
    domain_dir = KB_DIR / domain / "concepts"
    if not domain_dir.exists():
        return []

    concept_ids = []
    for md_file in domain_dir.glob('*.md'):
        concept_ids.append(md_file.stem)

    return concept_ids


def create_reset_concept(concept_id: str) -> Dict:
    """
    Create fresh SM-2 parameters for a concept.

    Args:
        concept_id: Concept identifier

    Returns:
        Fresh concept schedule entry
    """
    tomorrow = datetime.now(timezone.utc) + timedelta(days=1)

    return {
        "id": concept_id,
        "interval": SM2_DEFAULTS["initial_interval"],
        "easiness_factor": SM2_DEFAULTS["initial_easiness_factor"],
        "repetitions": SM2_DEFAULTS["initial_repetitions"],
        "next_review_date": tomorrow.strftime("%Y-%m-%d"),
        "last_review_date": None,
        "quality_history": []
    }


def confirm_reset(reset_type: str, target: str, force: bool, logger) -> bool:
    """
    Get user confirmation for schedule reset.

    Args:
        reset_type: Type of reset (full, domain, concept)
        target: Target identifier (domain name or concept ID)
        force: Skip confirmation if True
        logger: Logger instance

    Returns:
        True if confirmed, False otherwise
    """
    if force:
        logger.warning(f"Force mode enabled - skipping confirmation for {reset_type} reset")
        return True

    print()
    print("⚠️  WARNING: SCHEDULE RESET (NUCLEAR OPTION)")
    print("=" * 60)
    print(f"   Reset type: {reset_type}")
    print(f"   Target: {target}")
    print()
    print("   This will DELETE review history and progress.")
    print("   Concepts will restart from day 1.")
    print("   A backup will be created before reset.")
    print("=" * 60)
    print()

    response = input("Type 'RESET' to confirm (case-sensitive): ").strip()
    confirmed = response == 'RESET'

    if not confirmed:
        print("❌ Reset cancelled by user")

    return confirmed


def main():
    """Main entry point for reset-schedule script."""
    parser = argparse.ArgumentParser(
        description='Reset SM-2 spaced repetition schedule (NUCLEAR OPTION)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Reset operation selection
    reset_group = parser.add_mutually_exclusive_group(required=True)
    reset_group.add_argument('--full-reset', action='store_true',
                             help='Reset ALL concepts (nuclear option)')
    reset_group.add_argument('--reset-domain', type=str, metavar='DOMAIN',
                             help='Reset concepts in specific domain')
    reset_group.add_argument('--reset-concept', type=str, metavar='CONCEPT_ID',
                             help='Reset specific concept only')

    # Common options
    parser.add_argument('--force', action='store_true',
                        help='Skip confirmation prompts (for automation)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without writing files')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable DEBUG level logging')
    parser.add_argument('--quiet', action='store_true',
                        help='Minimize output (warnings only)')
    parser.add_argument('--backup-dir', type=str,
                        help='Custom backup directory')
    parser.add_argument('--no-backup', action='store_true',
                        help='Skip backup creation')

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging('reset-schedule', verbose=args.verbose, quiet=args.quiet)

    try:
        # Load existing schedule
        logger.info(f"Loading schedule from {SCHEDULE_PATH}...")
        schedule = load_schedule()
        original_count = len(schedule.get('concepts', {}))
        logger.info(f"Current schedule contains {original_count} concepts")

        # Determine reset operation
        concepts_to_reset = []

        if args.full_reset:
            # Full reset: all concepts
            concepts_to_reset = list(schedule.get('concepts', {}).keys())
            reset_type = "FULL"
            target = f"ALL ({len(concepts_to_reset)} concepts)"

        elif args.reset_domain:
            # Domain reset: concepts in specific domain
            domain = args.reset_domain
            all_domain_concepts = get_concepts_by_domain(domain)

            if not all_domain_concepts:
                logger.error(f"Domain not found or has no concepts: {domain}")
                return 2

            # Only reset concepts that exist in schedule
            concepts_to_reset = [
                cid for cid in schedule.get('concepts', {}).keys()
                if cid in all_domain_concepts
            ]

            reset_type = "DOMAIN"
            target = f"{domain} ({len(concepts_to_reset)}/{len(all_domain_concepts)} concepts in schedule)"

        elif args.reset_concept:
            # Single concept reset
            concept_id = args.reset_concept

            if concept_id not in schedule.get('concepts', {}):
                logger.error(f"Concept not found in schedule: {concept_id}")
                return 2

            concepts_to_reset = [concept_id]
            reset_type = "CONCEPT"
            target = concept_id

        else:
            logger.error("No reset operation specified")
            return 2

        if not concepts_to_reset:
            logger.warning("No concepts to reset")
            return 0

        logger.info(f"Will reset {len(concepts_to_reset)} concept(s)")

        # Confirmation required (unless dry-run or force)
        if not args.dry_run:
            if not confirm_reset(reset_type, target, args.force, logger):
                return 0

        # Perform reset
        logger.info(f"Resetting {len(concepts_to_reset)} concept(s)...")

        reset_count = 0
        for concept_id in concepts_to_reset:
            old_data = schedule['concepts'].get(concept_id, {})
            new_data = create_reset_concept(concept_id)

            logger.debug(f"Reset {concept_id}: "
                         f"interval {old_data.get('interval', 'N/A')} → {new_data['interval']}, "
                         f"EF {old_data.get('easiness_factor', 'N/A')} → {new_data['easiness_factor']}")

            schedule['concepts'][concept_id] = new_data
            reset_count += 1

        # Update metadata
        schedule['metadata']['last_review'] = None
        schedule['metadata']['concepts_due_today'] = len(concepts_to_reset)

        # Dry-run mode
        if args.dry_run:
            logger.info(f"DRY RUN - would reset {reset_count} concept(s)")
            logger.info(f"Would write to {SCHEDULE_PATH}")
            return 0

        # Check disk space
        if not check_disk_space(SCHEDULE_PATH, required_mb=1):
            logger.error("Insufficient disk space")
            return 3

        # Create backup
        if not args.no_backup and SCHEDULE_PATH.exists():
            backup_dir = Path(args.backup_dir) if args.backup_dir else None
            backup_path = create_backup(SCHEDULE_PATH, backup_dir)
            if backup_path:
                logger.info(f"✅ Backup created: {backup_path}")

        # Write schedule atomically
        REVIEW_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_json(SCHEDULE_PATH, schedule)
        logger.info(f"✅ Schedule reset complete: {reset_count} concept(s) reset")
        logger.info(f"Updated schedule: {SCHEDULE_PATH}")

        return 0

    except KeyboardInterrupt:
        logger.error("Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=args.verbose)
        return 1


if __name__ == '__main__':
    sys.exit(main())
