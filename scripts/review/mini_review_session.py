#!/usr/bin/env python3
"""
Mini Review Session - Select random due rem for review gating

Purpose: Support review-gated command execution by selecting 1 due rem
for mandatory review before learning/research tasks.

Design Philosophy:
- No hardcoded command lists (caller decides when to use)
- No hardcoded messages (returns data, AI generates dialogue)
- Flexible selection strategy (random from due/overdue pool)
- Minimal prompt approach (returns JSON instruction)
"""

import json
import random
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Dict, Any


def load_schedule(schedule_path: Path) -> Dict[str, Any]:
    """Load review schedule from JSON file."""
    if not schedule_path.exists():
        return {"concepts": {}}

    try:
        with open(schedule_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"concepts": {}}


def get_due_rems(schedule: Dict[str, Any]) -> list[Dict[str, Any]]:
    """
    Get all rems that are due or overdue for review.

    Returns:
        List of concept dicts with metadata
    """
    today = date.today()
    concepts = schedule.get('concepts', {})

    if isinstance(concepts, dict):
        concepts = concepts.values()

    due_rems = []
    for concept in concepts:
        fsrs_state = concept.get('fsrs_state', {})
        next_review = fsrs_state.get('next_review')

        if next_review:
            try:
                review_date = datetime.strptime(next_review, '%Y-%m-%d').date()
                if review_date <= today:
                    # Add metadata for selection priority
                    days_overdue = (today - review_date).days
                    concept['_days_overdue'] = days_overdue
                    due_rems.append(concept)
            except (ValueError, TypeError):
                continue

    return due_rems


def select_random_due_rem(
    schedule_path: Path,
    strategy: str = 'random'
) -> Optional[Dict[str, Any]]:
    """
    Select one rem for mini review session.

    Args:
        schedule_path: Path to schedule.json
        strategy: Selection strategy
            - 'random': Random from all due rems
            - 'most_overdue': Pick most overdue rem
            - 'least_reviewed': Pick rem with lowest review_count

    Returns:
        Rem metadata dict or None if no rems due
    """
    schedule = load_schedule(schedule_path)
    due_rems = get_due_rems(schedule)

    if not due_rems:
        return None

    if strategy == 'most_overdue':
        return max(due_rems, key=lambda r: r.get('_days_overdue', 0))
    elif strategy == 'least_reviewed':
        return min(due_rems, key=lambda r: r.get('fsrs_state', {}).get('review_count', 0))
    else:  # random (default)
        return random.choice(due_rems)


def format_review_instruction(
    rem_data: Dict[str, Any],
    original_command: str
) -> Dict[str, Any]:
    """
    Format minimal data for main agent to conduct mini review.

    Returns ONLY necessary data - NO workflow steps, NO messages.
    Main agent decides how to conduct review based on data alone.
    AI generates dialogue, workflow, and questions flexibly.
    """
    return {
        "action": "conduct_mini_review",
        "rem_to_review": {
            "id": rem_data.get('id'),
            "title": rem_data.get('title'),
            "domain": rem_data.get('domain'),
            "fsrs_state": rem_data.get('fsrs_state'),
            "days_overdue": rem_data.get('_days_overdue', 0)
        },
        "original_command": original_command
    }


def get_due_count(schedule_path: Path) -> Dict[str, int]:
    """
    Get count of due/overdue rems.

    Returns:
        {"overdue": N, "due_today": M, "total": N+M}
    """
    schedule = load_schedule(schedule_path)
    today = date.today()
    concepts = schedule.get('concepts', {})

    if isinstance(concepts, dict):
        concepts = concepts.values()

    overdue = 0
    due_today = 0

    for concept in concepts:
        fsrs_state = concept.get('fsrs_state', {})
        next_review = fsrs_state.get('next_review')

        if next_review:
            try:
                review_date = datetime.strptime(next_review, '%Y-%m-%d').date()
                if review_date < today:
                    overdue += 1
                elif review_date == today:
                    due_today += 1
            except (ValueError, TypeError):
                continue

    return {
        "overdue": overdue,
        "due_today": due_today,
        "total": overdue + due_today
    }


def main():
    """CLI interface for testing."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Select random due rem for mini review"
    )
    parser.add_argument(
        '--schedule',
        default='.review/schedule.json',
        help='Path to schedule.json'
    )
    parser.add_argument(
        '--strategy',
        choices=['random', 'most_overdue', 'least_reviewed'],
        default='random',
        help='Selection strategy'
    )
    parser.add_argument(
        '--command',
        default='/learn',
        help='Original command being gated'
    )
    parser.add_argument(
        '--count-only',
        action='store_true',
        help='Only show due count, no selection'
    )

    args = parser.parse_args()
    schedule_path = Path(args.schedule)

    if args.count_only:
        counts = get_due_count(schedule_path)
        print(json.dumps(counts, indent=2))
        return

    selected = select_random_due_rem(schedule_path, args.strategy)

    if not selected:
        result = {
            "status": "no_reviews_due",
            "message": "No rems due for review"
        }
    else:
        instruction = format_review_instruction(selected, args.command)
        result = {
            "status": "review_required",
            "instruction": instruction
        }

    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
