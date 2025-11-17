#!/usr/bin/env python3
import os
import sys
"""
UserPromptSubmit Hook: Gentle review reminder every 10th user input
Checks .review/schedule.json for overdue reviews and reminds user periodically
"""

import json
import sys
from datetime import datetime, date
from pathlib import Path

# Portable project root detection using CLAUDE_PROJECT_DIR
# This environment variable is set by Claude Code to the project root
PROJECT_DIR = Path(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()))



COUNTER_FILE = PROJECT_DIR / '.claude/hook-counter.json'
SCHEDULE_FILE = PROJECT_DIR / '.review/schedule.json'
REMINDER_INTERVAL = 10  # Remind every 10 prompts


def load_counter() -> int:
    """Load current prompt counter"""
    if not COUNTER_FILE.exists():
        return 0
    try:
        with open(COUNTER_FILE, 'r') as f:
            data = json.load(f)
            return data.get('prompt_count', 0)
    except (json.JSONDecodeError, IOError):
        return 0


def save_counter(count: int):
    """Save updated prompt counter"""
    try:
        COUNTER_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(COUNTER_FILE, 'w') as f:
            json.dump({'prompt_count': count}, f)
    except IOError:
        pass


def count_overdue_reviews() -> int:
    """Count concepts that are overdue for review"""
    if not SCHEDULE_FILE.exists():
        return 0

    try:
        with open(SCHEDULE_FILE, 'r') as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return 0

    today = date.today()
    concepts = data.get('concepts', {})

    # Handle both dict and list formats
    if isinstance(concepts, dict):
        concepts = concepts.values()

    # Count overdue (not just due today, but past due)
    overdue_count = 0
    for concept in concepts:
        fsrs_state = concept.get('fsrs_state', {})
        next_review = fsrs_state.get('next_review')
        if next_review:
            try:
                review_date = datetime.strptime(next_review, '%Y-%m-%d').date()
                if review_date <= today:  # Due today or overdue
                    overdue_count += 1
            except (ValueError, TypeError):
                continue

    return overdue_count


def main():
    """Main hook execution"""
    try:
        # Increment counter
        current_count = load_counter()
        new_count = current_count + 1
        save_counter(new_count)

        # Check if it's time to remind (every 10th prompt)
        if new_count % REMINDER_INTERVAL == 0:
            overdue_count = count_overdue_reviews()

            if overdue_count > 0:
                print(f"📚 Reminder: {overdue_count} concept{'s' if overdue_count != 1 else ''} overdue for review. Run /review when convenient.")

        # Always exit 0 (never block user input)
        sys.exit(0)

    except Exception as e:
        # Silent fail - never block user input
        sys.exit(0)


if __name__ == '__main__':
    main()
