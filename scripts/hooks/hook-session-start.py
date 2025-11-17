#!/usr/bin/env python3
"""
SessionStart Hook: Display count of due reviews on session startup
Reads .review/schedule.json and counts concepts where next_review_date <= today
"""

import os
import sys
import json
from datetime import datetime, date
from pathlib import Path

# Portable project root detection using CLAUDE_PROJECT_DIR
# This environment variable is set by Claude Code to the project root
PROJECT_DIR = Path(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()))


def count_due_reviews(schedule_file: Path) -> int:
    """Count concepts due for review"""
    if not schedule_file.exists():
        return 0

    try:
        with open(schedule_file, 'r') as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return 0

    today = date.today()
    concepts = data.get('concepts', {})

    # Handle both dict and list formats
    if isinstance(concepts, dict):
        concepts = concepts.values()

    due_count = sum(
        1 for concept in concepts
        if concept.get('next_review_date') and
        datetime.strptime(concept['next_review_date'], '%Y-%m-%d').date() <= today
    )

    return due_count


def main():
    """Main hook execution"""
    try:
        # Path relative to project root
        schedule_file = PROJECT_DIR / '.review/schedule.json'

        due_count = count_due_reviews(schedule_file)

        if due_count > 0:
            print(f"📚 {due_count} concept{'s' if due_count != 1 else ''} due for review. Run /review when ready.")

        # Always exit 0 (don't block session start)
        sys.exit(0)

    except Exception as e:
        # Silent fail - don't block session start
        sys.exit(0)


if __name__ == '__main__':
    main()
