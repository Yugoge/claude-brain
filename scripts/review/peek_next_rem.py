#!/usr/bin/env python3
"""
Peek at the Rem after the next pending one in a review session.

Used by the prefetch pipeline: while the main agent presents Q(N),
this script returns Q(N+1) so the agent can prefetch its review-master
consultation in the background.

Unlike get_next_rem.py which returns the FIRST pending Rem,
this returns the SECOND pending Rem (the one after next).

Usage:
    source venv/bin/activate && python scripts/review/peek_next_rem.py --session-id <uuid>

Exit codes: 0=found, 1=error, 2=no second pending Rem
"""

import json
import sys
import argparse
from pathlib import Path

SESSION_DIR = Path('.review')


def session_file_for(session_id: str) -> Path:
    """Return the session file path for a given session_id."""
    return SESSION_DIR / f'session-{session_id}.json'


def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description='Peek at second pending Rem')
    parser.add_argument('--session-id', required=True, help='UUID of the review session')
    return parser.parse_args()


def load_session(session_id: str):
    """Load session file. Returns (session_dict, error_str)."""
    sf = session_file_for(session_id)
    if not sf.exists():
        return None, f"Session file not found: {sf.name}"
    try:
        with open(sf, 'r', encoding='utf-8') as f:
            return json.load(f), None
    except (json.JSONDecodeError, IOError) as e:
        return None, f"Failed to read session file: {e}"


def find_pending_rems(rems, start_index):
    """Find all pending Rems from start_index onward. Returns list of (rem, index)."""
    pending = []
    for i in range(start_index, len(rems)):
        if rems[i].get('status', 'pending') == 'pending':
            pending.append((rems[i], i))
    return pending


def make_rem_entry(rem):
    """Extract id, path, conversation_source from a Rem dict."""
    return {
        'id': rem['id'],
        'path': rem['path'],
        'conversation_source': rem.get('conversation_source'),
    }


def peek_next(session_id: str):
    """Return the second pending Rem (the one after the next one to review)."""
    session, error = load_session(session_id)
    if error:
        return {'success': False, 'error': error}

    rems = session.get('rems', [])
    start = session.get('current_index', 0)
    pending = find_pending_rems(rems, start)

    if len(pending) < 2:
        return {
            'success': True,
            'peek_rem': None,
            'message': 'No second pending Rem (last Rem or session nearly complete)',
        }

    second_rem, second_idx = pending[1]
    return {
        'success': True,
        'peek_rem': make_rem_entry(second_rem),
        'peek_index': second_idx,
        'total': session.get('total', 0),
    }


def main():
    """Entry point."""
    args = parse_args()
    result = peek_next(args.session_id)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result.get('success'):
        sys.exit(1)
    if result.get('peek_rem') is None:
        sys.exit(2)
    sys.exit(0)


if __name__ == '__main__':
    main()
