#!/usr/bin/env python3
"""
Get Prerequisite Titles for Review Suggestions

Extract prerequisite Rem titles from backlinks index.
Used for contextual messages during review.

Usage:
    source venv/bin/activate && source venv/bin/activate && python scripts/review/get_prerequisite_titles.py <rem-id>

Output: Comma-separated prerequisite titles or empty string
"""

import json
import sys
from pathlib import Path

def load_schedule():
    """Load review schedule for title lookup"""
    schedule_path = Path('.review/schedule.json')
    if not schedule_path.exists():
        return {}

    with open(schedule_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('concepts', {})

def get_prerequisite_titles(rem_id):
    """
    Get prerequisite titles for a Rem.

    Args:
        rem_id: Target Rem ID

    Returns:
        Comma-separated string of prerequisite titles
    """
    # Load linked rems
    sys.path.append('scripts/review')
    from get_linked_rems import get_linked_rems

    linked_data = get_linked_rems(rem_id, priority_filter='prerequisites')
    linked_rems = linked_data.get('linked_rems', [])

    if not linked_rems:
        return ""

    # Load schedule for title lookup
    schedule = load_schedule()

    # Extract prerequisite titles
    titles = []
    for link in linked_rems:
        prereq_id = link['id']
        if prereq_id in schedule:
            title = schedule[prereq_id].get('title', prereq_id)
            titles.append(title)

    return ", ".join(titles)

def main():
    if len(sys.argv) < 2:
        print("", end='')
        return

    rem_id = sys.argv[1]
    titles = get_prerequisite_titles(rem_id)
    print(titles, end='')

if __name__ == '__main__':
    main()
