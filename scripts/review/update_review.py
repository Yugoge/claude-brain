#!/usr/bin/env python3
"""
Helper script for review-master agent to update FSRS schedule after each review.

Usage:
    source venv/bin/activate && python scripts/review/update_review.py <concept_id> <rating> [--session-id <uuid>]

Arguments:
    concept_id: Rem ID
    rating: User's self-rating (1-4: Again, Hard, Good, Easy)
    --session-id: UUID of the review session (optional for backward compat)

Returns:
    JSON output with updated FSRS state for user feedback
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add review scripts to path
sys.path.append('scripts/review')
from review_scheduler import ReviewScheduler


def find_single_session_file():
    """Find a single active session file for backward compat (no --session-id)."""
    session_dir = Path('.review')
    if not session_dir.exists():
        return None
    files = sorted(session_dir.glob('session-*.json'))
    if len(files) == 1:
        return files[0]
    return None  # Ambiguous or no sessions


def update_session_state(concept_id, rating, session_id=None):
    """Mark Rem as reviewed in session file and advance current_index.

    Root cause fix: Session state must be persisted to disk so main agent
    can recover the Rem list after context loss.
    """
    import tempfile, os
    if session_id:
        session_path = Path(f'.review/session-{session_id}.json')
    else:
        # Backward compat: try to find single active session
        session_path = find_single_session_file()
    if not session_path or not session_path.exists():
        return  # No active session (e.g., non-blind mode review)
    try:
        with open(session_path, 'r', encoding='utf-8') as f:
            session = json.load(f)
    except (json.JSONDecodeError, IOError):
        return  # Corrupted session file, skip update
    rems = session.get('rems', [])
    updated = False
    for i, rem in enumerate(rems):
        if rem.get('id') == concept_id and rem.get('status') == 'pending':
            rem['status'] = 'reviewed'
            rem['rating'] = rating
            rem['reviewed_at'] = datetime.now().isoformat()
            # Advance current_index past this Rem
            if session.get('current_index', 0) <= i:
                session['current_index'] = i + 1
            updated = True
            break
    if not updated:
        return
    # Atomic write
    temp_fd, temp_path = tempfile.mkstemp(dir=str(session_path.parent), suffix='.tmp')
    try:
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            json.dump(session, f, indent=2, ensure_ascii=False)
        os.rename(temp_path, str(session_path))
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def main():
    # Parse arguments: concept_id rating [--session-id <uuid>]
    import argparse
    parser = argparse.ArgumentParser(description='Update FSRS review')
    parser.add_argument('concept_id', help='Rem ID')
    parser.add_argument('rating', type=int, choices=[1, 2, 3, 4],
                        help='Rating 1-4 (Again, Hard, Good, Easy)')
    parser.add_argument('--session-id', default=None,
                        help='UUID of the review session')
    args = parser.parse_args()

    concept_id = args.concept_id
    rating = args.rating
    session_id = args.session_id

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

    # Atomic write: write to temp file, then rename
    temp_path = None
    try:
        import tempfile, os
        temp_fd, temp_path = tempfile.mkstemp(
            dir=str(schedule_path.parent), suffix='.tmp'
        )
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            json.dump(schedule, f, indent=2, ensure_ascii=False)
        os.rename(temp_path, str(schedule_path))
    except Exception as e:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
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

    # Update session file to mark Rem as reviewed
    update_session_state(concept_id, rating, session_id)

    print(json.dumps(output, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
