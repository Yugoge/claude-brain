#!/usr/bin/env python3
"""
Helper script for review-master agent to update FSRS schedule after each review.

Usage:
    python scripts/review/update_review.py <concept_id> <rating>

Arguments:
    concept_id: Rem ID (e.g., "french-time-expressions")
    rating: User's self-rating (1-4: Again, Hard, Good, Easy)

Returns:
    JSON output with updated FSRS state for user feedback
"""

import sys
import json
from pathlib import Path

# Add review scripts to path
sys.path.append('scripts/review')
from review_scheduler import ReviewScheduler

def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/review/update_review.py <concept_id> <rating>", file=sys.stderr)
        sys.exit(1)

    concept_id = sys.argv[1]
    try:
        rating = int(sys.argv[2])
        if rating not in [1, 2, 3, 4]:
            raise ValueError("Rating must be 1-4")
    except ValueError as e:
        print(f"Error: Invalid rating. Must be 1-4 (Again, Hard, Good, Easy). Got: {sys.argv[2]}", file=sys.stderr)
        sys.exit(1)

    schedule_path = Path('.review/schedule.json')

    # Load schedule
    try:
        with open(schedule_path, 'r', encoding='utf-8') as f:
            schedule = json.load(f)
    except FileNotFoundError:
        print(f"Error: Schedule file not found at {schedule_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in schedule file: {e}", file=sys.stderr)
        sys.exit(1)

    # Check if concept exists
    if concept_id not in schedule['concepts']:
        print(f"Error: Concept '{concept_id}' not found in schedule", file=sys.stderr)
        available = list(schedule['concepts'].keys())[:5]
        print(f"Available concepts (first 5): {available}", file=sys.stderr)
        sys.exit(1)

    # Get concept
    concept = schedule['concepts'][concept_id]

    # Store old state for comparison
    old_fsrs = concept['fsrs_state'].copy()

    # Initialize scheduler and update
    scheduler = ReviewScheduler()
    updated_rem = scheduler.schedule_review(concept, rating)

    # Save back to schedule
    schedule['concepts'][concept_id] = updated_rem

    try:
        with open(schedule_path, 'w', encoding='utf-8') as f:
            json.dump(schedule, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error: Failed to save schedule: {e}", file=sys.stderr)
        sys.exit(1)

    # Print results for agent to parse and show user
    new_fsrs = updated_rem['fsrs_state']

    rating_names = {1: "Again", 2: "Hard", 3: "Good", 4: "Easy"}

    output = {
        "success": True,
        "concept_id": concept_id,
        "rating": rating,
        "rating_name": rating_names[rating],
        "old_state": {
            "difficulty": round(old_fsrs['difficulty'], 2),
            "stability": round(old_fsrs['stability'], 2),
            "next_review": old_fsrs['next_review'],
            "review_count": old_fsrs['review_count']
        },
        "new_state": {
            "difficulty": round(new_fsrs['difficulty'], 2),
            "stability": round(new_fsrs['stability'], 2),
            "retrievability": round(new_fsrs['retrievability'], 2),
            "next_review": new_fsrs['next_review'],
            "interval": new_fsrs['interval'],
            "review_count": new_fsrs['review_count']
        },
        "changes": {
            "difficulty_delta": round(new_fsrs['difficulty'] - old_fsrs['difficulty'], 2),
            "stability_delta": round(new_fsrs['stability'] - old_fsrs['stability'], 2),
            "interval_days": new_fsrs['interval']
        }
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
